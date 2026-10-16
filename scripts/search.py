"""Run a logged search against a scriptable source and save the raw export.

Usage:
    python scripts/search.py SOURCE SEARCH_ID "QUERY" [--round pilot|main|update]
                             [--until YYYY-MM-DD] [--since YYYY-MM-DD] [--top N]
                             [--run-by R1] [--note TEXT]

SOURCE: openalex | semanticscholar | arxiv | europepmc | crossref | doaj   (official APIs)
        ieee | springer | scholar   (the sites' own web search endpoints, read as a browser would)
QUERY is passed to the source in its own syntax (see protocol/search_strings.md).
--top caps the export to the first N results by relevance (crossref, scholar).
--prefix restricts crossref to one DOI prefix (10.1016 = Elsevier, 10.1145 = ACM).

The scholar adapter waits 8-15 s between pages and stops at the first CAPTCHA,
logging whatever was retrieved with a note; it never tries to get past a CAPTCHA.

Writes data/raw_exports/<SEARCH_ID>_<SOURCE>_<date>.raw.json (raw API pages) and
.csv (flat records), and appends one row to data/search_log.csv.

Optional environment variables: OPENALEX_MAILTO, OPENALEX_API_KEY, S2_API_KEY.
"""
import argparse
import csv
import datetime as dt
import html
import http.cookiejar
import json
import os
import pathlib
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
# API keys live in the gitignored .env file (KEY=value lines); real environment variables win.
if (ROOT / ".env").exists():
    for _line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())
EXPORTS = ROOT / "data" / "raw_exports"
SEARCH_LOG = ROOT / "data" / "search_log.csv"
EXPORT_COLUMNS = ["source_record_id", "title", "authors", "year", "venue", "work_type",
                  "doi", "url", "abstract", "keywords", "cited_by_count"]
USER_AGENT = "spikingHSI-systematic-review/1.0 (mailto:%s)" % os.environ.get("OPENALEX_MAILTO", "unknown")


def fetch(url, headers=None, as_json=True, pause=0.0):
    headers = {"User-Agent": USER_AGENT, **(headers or {})}
    for attempt in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=90) as resp:
                body = resp.read()
            time.sleep(pause)
            return json.loads(body) if as_json else body
        except urllib.error.HTTPError as e:
            retryable = e.code == 429 or e.code >= 500
            if attempt == 7 or not retryable:
                raise SystemExit(f"HTTP {e.code}: {e.read()[:500]!r}\nURL: {url}")
        except urllib.error.URLError:
            if attempt == 7:
                raise
        time.sleep(min(60, 3 * 2 ** attempt))


def clean_doi(doi):
    doi = (doi or "").strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    return doi


def record(**kw):
    row = {c: "" for c in EXPORT_COLUMNS}
    row.update({k: ("" if v is None else v) for k, v in kw.items()})
    row["doi"] = clean_doi(row["doi"])
    for k in ("title", "abstract", "venue"):
        row[k] = " ".join(str(row[k]).split())
    return row


OPENALEX_SELECT = ("id,doi,title,publication_year,type,primary_location,authorships,"
                   "abstract_inverted_index,cited_by_count,keywords")


def openalex_record(w):
    """One OpenAlex work (fields OPENALEX_SELECT) as an export row."""
    inv = w.get("abstract_inverted_index") or {}
    abstract = " ".join(word for _, word in sorted((p, wd) for wd, ps in inv.items() for p in ps))
    loc = w.get("primary_location") or {}
    return record(
        source_record_id=w["id"].rsplit("/", 1)[-1], title=w.get("title"),
        authors=";".join(a["author"]["display_name"] for a in w.get("authorships") or []),
        year=w.get("publication_year"), venue=(loc.get("source") or {}).get("display_name"),
        work_type=w.get("type"), doi=w.get("doi"), url=loc.get("landing_page_url") or w["id"],
        abstract=abstract, keywords=";".join(k["display_name"] for k in w.get("keywords") or []),
        cited_by_count=w.get("cited_by_count"))


def openalex_params(**params):
    """Add the polite-pool mailto and the API key, when set."""
    for env, key in (("OPENALEX_MAILTO", "mailto"), ("OPENALEX_API_KEY", "api_key")):
        if os.environ.get(env):
            params[key] = os.environ[env]
    return params


# --- source adapters: each returns (total_hits, raw_pages, records, filters_text) ---

def openalex(query, args):
    filters = [f"title_and_abstract.search:{query}"]
    extra = []
    if args.since:
        extra.append(f"from_publication_date:{args.since}")
    if args.until:
        extra.append(f"to_publication_date:{args.until}")
    # Page paging needs no API key (cursor paging does) and reaches 10,000 results.
    params = openalex_params(filter=",".join(filters + extra), page=1, select=OPENALEX_SELECT,
                             **{"per-page": 200})
    pages, rows, total = [], [], 0
    while True:
        page = fetch("https://api.openalex.org/works?" + urllib.parse.urlencode(params))
        pages.append(page)
        total = page["meta"]["count"]
        rows += [openalex_record(w) for w in page["results"]]
        if not page["results"] or len(rows) >= total or len(rows) >= args.top:
            break
        if len(rows) >= 10_000:
            raise SystemExit("More than 10,000 hits: narrow the query.")
        params["page"] += 1
    return total, pages, rows, ";".join(extra)


def semanticscholar(query, args):
    params = {"query": query, "fields": "title,authors,year,venue,publicationTypes,externalIds,"
                                        "url,abstract,citationCount"}
    if args.since or args.until:
        params["publicationDateOrYear"] = f"{args.since or ''}:{args.until or ''}"
    headers = {"x-api-key": os.environ["S2_API_KEY"]} if os.environ.get("S2_API_KEY") else {}
    pages, rows, total = [], [], 0
    while True:
        page = fetch("https://api.semanticscholar.org/graph/v1/paper/search/bulk?"
                     + urllib.parse.urlencode(params), headers, pause=1.1)
        pages.append(page)
        total = page.get("total", 0)
        for p in page.get("data") or []:
            ext = p.get("externalIds") or {}
            rows.append(record(
                source_record_id=p["paperId"], title=p.get("title"),
                authors=";".join(a.get("name") or "" for a in p.get("authors") or []),
                year=p.get("year"), venue=p.get("venue"),
                work_type=";".join(p.get("publicationTypes") or []), doi=ext.get("DOI"),
                url=p.get("url"), abstract=p.get("abstract"), cited_by_count=p.get("citationCount")))
        if not page.get("token") or len(rows) >= args.top:
            break
        params["token"] = page["token"]
    return total, pages, rows, params.get("publicationDateOrYear", "")


def arxiv(query, args):
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom",
          "os": "http://a9.com/-/spec/opensearch/1.1/"}
    if args.since or args.until:
        lo = (args.since or "1990-01-01").replace("-", "") + "0000"
        hi = (args.until or "2100-01-01").replace("-", "") + "2359"
        query = f"({query}) AND submittedDate:[{lo} TO {hi}]"
    pages, rows, start, total = [], [], 0, 0
    while True:
        params = {"search_query": query, "start": start, "max_results": 200,
                  "sortBy": "submittedDate", "sortOrder": "descending"}
        body = fetch("https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params),
                     as_json=False, pause=3.5)
        pages.append(body.decode("utf-8"))
        feed = ET.fromstring(body)
        total = int(feed.find("os:totalResults", ns).text)
        entries = feed.findall("a:entry", ns)
        for e in entries:
            text = lambda tag, space="a": (e.find(f"{space}:{tag}", ns).text if e.find(f"{space}:{tag}", ns) is not None else "")
            arxiv_id = text("id").rsplit("/abs/", 1)[-1]
            rows.append(record(
                source_record_id=arxiv_id, title=text("title"),
                authors=";".join(a.find("a:name", ns).text for a in e.findall("a:author", ns)),
                year=text("published")[:4], venue=text("journal_ref", "x") or "arXiv",
                work_type="preprint", doi=text("doi", "x") or f"10.48550/arxiv.{arxiv_id.split('v')[0]}",
                url=text("id"), abstract=text("summary"),
                keywords=";".join(c.get("term") for c in e.findall("a:category", ns))))
        start += len(entries)
        if not entries or start >= total or start >= args.top:
            break
    return total, pages, rows, "submittedDate" if (args.since or args.until) else ""


def europepmc(query, args):
    if args.since or args.until:
        query = f"({query}) AND FIRST_PDATE:[{args.since or '1900-01-01'} TO {args.until or '2100-12-31'}]"
    params = {"query": query, "format": "json", "resultType": "core", "pageSize": 1000, "cursorMark": "*"}
    pages, rows, total = [], [], 0
    while True:
        page = fetch("https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(params))
        pages.append(page)
        total = page.get("hitCount", 0)
        results = page.get("resultList", {}).get("result", [])
        for r in results:
            journal = ((r.get("journalInfo") or {}).get("journal") or {}).get("title")
            rows.append(record(
                source_record_id=f"{r.get('source')}:{r.get('id')}", title=r.get("title"),
                authors=";".join(a.get("fullName", "") for a in (r.get("authorList") or {}).get("author", [])),
                year=r.get("pubYear"), venue=journal or r.get("bookOrReportDetails", {}).get("publisher"),
                work_type=";".join((r.get("pubTypeList") or {}).get("pubType", [])), doi=r.get("doi"),
                url=f"https://europepmc.org/article/{r.get('source')}/{r.get('id')}",
                abstract=r.get("abstractText"),
                keywords=";".join((r.get("keywordList") or {}).get("keyword", [])),
                cited_by_count=r.get("citedByCount")))
        nxt = page.get("nextCursorMark")
        if not results or not nxt or nxt == params["cursorMark"] or len(rows) >= args.top:
            break
        params["cursorMark"] = nxt
    return total, pages, rows, "FIRST_PDATE" if (args.since or args.until) else ""


def crossref(query, args):
    # Publication types only: drops peer-review reports, components and datasets.
    filt = ["type:journal-article", "type:proceedings-article", "type:posted-content",
            "type:book-chapter"]
    if args.since:
        filt.append(f"from-pub-date:{args.since}")
    if args.until:
        filt.append(f"until-pub-date:{args.until}")
    if args.prefix:
        filt.append(f"prefix:{args.prefix}")
    params = {"query.bibliographic": query, "rows": min(args.top, 1000), "sort": "relevance",
              "select": "DOI,title,author,container-title,issued,type,abstract,URL,is-referenced-by-count"}
    if filt:
        params["filter"] = ",".join(filt)
    if os.environ.get("OPENALEX_MAILTO"):
        params["mailto"] = os.environ["OPENALEX_MAILTO"]
    page = fetch("https://api.crossref.org/works?" + urllib.parse.urlencode(params))
    rows = []
    for it in page["message"]["items"]:
        issued = ((it.get("issued") or {}).get("date-parts") or [[None]])[0][0]
        rows.append(record(
            source_record_id=it.get("DOI"), title=" ".join(it.get("title") or []),
            authors=";".join(" ".join(filter(None, [a.get("given"), a.get("family")])) or a.get("name", "")
                             for a in it.get("author") or []),
            year=issued, venue=" ".join(it.get("container-title") or []), work_type=it.get("type"),
            doi=it.get("DOI"), url=it.get("URL"),
            abstract=re.sub(r"<[^>]+>", " ", it.get("abstract") or ""),
            cited_by_count=it.get("is-referenced-by-count")))
    filters = ";".join(filt + [f"top{args.top}_by_relevance"])
    return page["message"]["total-results"], [page], rows, filters


def doaj(query, args):
    pages, rows, page_no, total = [], [], 1, 0
    while True:
        url = (f"https://doaj.org/api/search/articles/{urllib.parse.quote(query, safe='')}"
               f"?page={page_no}&pageSize=100")
        page = fetch(url, pause=0.5)
        pages.append(page)
        total = page.get("total", 0)
        for r in page.get("results", []):
            b = r.get("bibjson", {})
            doi = next((i.get("id") for i in b.get("identifier", []) if i.get("type") == "doi"), "")
            link = next((l.get("url") for l in b.get("link", [])), "")
            rows.append(record(
                source_record_id=r.get("id"), title=b.get("title"),
                authors=";".join(a.get("name", "") for a in b.get("author", [])),
                year=b.get("year"), venue=(b.get("journal") or {}).get("title"), work_type="article",
                doi=doi, url=link, abstract=b.get("abstract"), keywords=";".join(b.get("keywords", []))))
        if not page.get("results") or len(rows) >= total or len(rows) >= args.top:
            break
        page_no += 1
    return total, pages, rows, ""


BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/140.0 Safari/537.36")


def strip_tags(text):
    return html.unescape(re.sub(r"<[^>]+>", " ", text or ""))


def first(pattern, text):
    m = re.search(pattern, text, re.S)
    return m.group(1) if m else ""


def year_ok(year, args):
    """Client-side date filter for sources whose web search has none."""
    if not year:
        return True
    return (not args.since or year >= args.since[:4]) and (not args.until or year <= args.until[:4])


def ieee(query, args):
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [("User-Agent", BROWSER_UA)]
    opener.open("https://ieeexplore.ieee.org/Xplore/home.jsp", timeout=60).read()
    pages, rows, page_no, total = [], [], 1, 0
    body = {"queryText": query, "rowsPerPage": 100, "returnType": "SEARCH"}
    if args.since or args.until:
        body["ranges"] = [f"{(args.since or '1800')[:4]}_{(args.until or '2100')[:4]}_Year"]
    while True:
        req = urllib.request.Request(
            "https://ieeexplore.ieee.org/rest/search", data=json.dumps({**body, "pageNumber": page_no}).encode(),
            headers={"Content-Type": "application/json", "Accept": "application/json",
                     "Origin": "https://ieeexplore.ieee.org",
                     "Referer": "https://ieeexplore.ieee.org/search/searchresult.jsp"})
        page = json.load(opener.open(req, timeout=90))
        pages.append(page)
        total = page.get("totalRecords", 0)
        records = page.get("records") or []
        for r in records:
            rows.append(record(
                source_record_id=r.get("articleNumber"), title=strip_tags(r.get("articleTitle")),
                authors=";".join(a.get("preferredName", "") for a in r.get("authors") or []),
                year=r.get("publicationYear"), venue=strip_tags(r.get("publicationTitle")),
                work_type=r.get("contentType"), doi=r.get("doi"),
                url="https://ieeexplore.ieee.org" + (r.get("documentLink") or ""),
                abstract=strip_tags(r.get("abstract")), cited_by_count=r.get("citationCount")))
        if not records or len(rows) >= total or len(rows) >= args.top:
            break
        page_no += 1
        time.sleep(2)
    return total, pages, rows, ";".join(body.get("ranges", []))


def parse_springer(text, args):
    """One SpringerLink results page -> (total hits, records, number of result items)."""
    m = re.search(r"Showing [\d,]+-[\d,]+ of ([\d,]+) results", text)
    total = int(m.group(1).replace(",", "")) if m else 0
    items = text.split('data-test="search-result-item"')[1:]
    rows = []
    for it in items:
        link = re.search(r'href="(/(?:article|chapter|book|referenceworkentry|protocol)/([^"]+))"', it)
        year = first(r'data-test="published">[^<]*?(\d{4})', it)
        if not year_ok(year, args):
            continue
        rows.append(record(
            source_record_id=link.group(2) if link else "",
            title=strip_tags(first(r'data-test="title">.*?<span>(.*?)</span>', it)),
            authors=strip_tags(first(r'data-test="authors">(.*?)</span>', it)).replace(", ", ";"),
            year=year, venue=strip_tags(first(r'data-test="parent"[^>]*>(.*?)</a>', it)),
            work_type=strip_tags(first(r'class="c-meta__type">(.*?)</span>', it)),
            doi=link.group(2) if link else "",
            url="https://link.springer.com" + link.group(1) if link else "",
            abstract=strip_tags(first(r'data-test="description">(.*?)</div>', it))))
    return total, rows, len(items)


def springer(query, args):
    pages, rows, page_no, total = [], [], 1, 0
    while True:
        url = ("https://link.springer.com/search?" +
               urllib.parse.urlencode({"new-search": "true", "query": query, "page": page_no}))
        text = fetch(url, {"User-Agent": BROWSER_UA}, as_json=False, pause=2).decode("utf-8")
        if "Client Challenge" in text or "search-result-item" not in text and "Showing" not in text:
            raise SystemExit("SpringerLink served a bot challenge; nothing logged. Use scripts/browser_search.py.")
        pages.append(text)
        total, page_rows, n_items = parse_springer(text, args)
        rows.extend(page_rows)
        if not n_items or page_no * 20 >= total or len(rows) >= args.top:
            break
        page_no += 1
    return total, pages, rows, "client_year_filter" if (args.since or args.until) else ""


def scholar_blocked(text):
    """Return a note if Scholar served a CAPTCHA or rate-limit page instead of results."""
    if "gs_captcha" in text or "unusual traffic" in text.lower():
        return "CAPTCHA"
    if "can&#39;t perform the operation now" in text or "can't perform the operation now" in text:
        return "rate limit ('try again later')"
    return ""


def parse_scholar(text):
    """One Google Scholar results page -> (hit count shown, records)."""
    m = re.search(r"About ([\d,]+) results|([\d,]+) results?", text)
    total = int((m.group(1) or m.group(2)).replace(",", "")) if m else 0
    rows = []
    for b in text.split('class="gs_ri"')[1:]:
        h3 = first(r'(<h3 class="gs_rt".*?</h3>)', b)
        link = first(r'<a [^>]*href="([^"]+)"', h3)
        title = strip_tags(re.sub(r'<span class="gs_ct[a-z0-9]*".*?</span>', "", h3, flags=re.S))
        # Scholar separates authors / venue, year / host with "\xa0- "; \s matches the nbsp.
        parts = [p.strip() for p in re.split(r"\s+-\s+", strip_tags(first(r'<div class="gs_a">(.*?)</div>', b)))]
        venue_year = parts[1] if len(parts) > 1 else ""
        rows.append(record(
            title=title, authors=parts[0].replace(", ", ";"),
            year=first(r"((?:19|20)\d{2})", venue_year),
            venue=re.sub(r",?\s*(19|20)\d{2}$", "", venue_year).strip(" ,"),
            url=html.unescape(link), work_type="citation" if "[CITATION]" in h3 else "",
            abstract=strip_tags(first(r'<div class="gs_rs">(.*?)</div>', b))))
    return total, rows


def scholar(query, args):
    pages, rows, start, total, note = [], [], 0, 0, ""
    params = {"q": query, "hl": "en"}
    if args.since:
        params["as_ylo"] = args.since[:4]
    if args.until:
        params["as_yhi"] = args.until[:4]
    while start < args.top:
        url = "https://scholar.google.com/scholar?" + urllib.parse.urlencode({**params, "start": start})
        try:
            text = fetch(url, {"User-Agent": BROWSER_UA}, as_json=False).decode("utf-8", "replace")
        except SystemExit as e:
            note = f"stopped at start={start}: {str(e)[:80]}"
            break
        blocked = scholar_blocked(text)
        if blocked:
            note = f"PARTIAL: Scholar {blocked} at start={start}"
            break
        pages.append(text)
        page_total, page_rows = parse_scholar(text)
        if start == 0:
            total = page_total
        rows.extend(page_rows)
        # Scholar pages often hold 9 results, so only an empty page or the hit count ends a query.
        start += 10
        if not page_rows or start >= total:
            break
        time.sleep(random.uniform(8, 15))
    filters = ";".join(filter(None, [f"top{args.top}", "as_ylo/as_yhi" if (args.since or args.until) else "", note]))
    return total, pages, rows, filters


ADAPTERS = {"openalex": openalex, "semanticscholar": semanticscholar, "arxiv": arxiv,
            "europepmc": europepmc, "crossref": crossref, "doaj": doaj,
            "ieee": ieee, "springer": springer, "scholar": scholar}
FIELDS = {"openalex": "title_abstract", "semanticscholar": "title_abstract", "arxiv": "all",
          "europepmc": "title_abstract", "crossref": "bibliographic", "doaj": "all",
          "ieee": "all_metadata", "springer": "full_text", "scholar": "full_text"}
INTERFACE = {"ieee": "web", "springer": "web", "scholar": "web"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", choices=sorted(ADAPTERS))
    ap.add_argument("search_id")
    ap.add_argument("query")
    ap.add_argument("--round", default="pilot", choices=["pilot", "main", "update"])
    ap.add_argument("--until", help="publication-date upper bound (search cut-off)")
    ap.add_argument("--since", help="publication-date lower bound (update searches)")
    ap.add_argument("--top", type=int, default=10_000, help="export at most N results")
    ap.add_argument("--prefix", help="crossref only: restrict to a DOI prefix")
    ap.add_argument("--run-by", default="R1")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    check_new(args.search_id, args.source)
    total, pages, rows, filters = ADAPTERS[args.source](args.query, args)
    save_export(args.search_id, args.source, args.query, total, pages, rows[:args.top], filters, args,
                INTERFACE.get(args.source, "API"), FIELDS[args.source])


def export_paths(search_id, source):
    stem = f"{search_id}_{source}_{dt.date.today().isoformat()}"
    return EXPORTS / f"{stem}.raw.json", EXPORTS / f"{stem}.csv"


def check_new(search_id, source):
    if any(p.exists() for p in export_paths(search_id, source)):
        raise SystemExit(f"{search_id}_{source} already exists today; raw exports are never overwritten.")


def save_export(search_id, source, query, total, pages, rows, filters, args, interface, fields):
    """Write the raw pages and flat records, and append the search to search_log.csv."""
    raw_path, csv_path = export_paths(search_id, source)
    EXPORTS.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    with SEARCH_LOG.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            search_id, dt.date.today().isoformat(), source, interface, fields, query,
            filters or "none", total, len(rows), csv_path.relative_to(ROOT).as_posix(),
            args.round, args.run_by, args.note])
    print(f"{search_id} {source}: {total} hits, {len(rows)} exported -> {csv_path.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
