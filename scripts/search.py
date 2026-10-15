"""Run a logged search against a scriptable source and save the raw export.

Usage:
    python scripts/search.py SOURCE SEARCH_ID "QUERY" [--round pilot|main|update]
                             [--until YYYY-MM-DD] [--since YYYY-MM-DD] [--top N]
                             [--run-by R1] [--note TEXT]

SOURCE: openalex | semanticscholar | arxiv | europepmc | crossref | doaj
QUERY is passed to the source in its own syntax (see protocol/search_strings.md).
--top caps the export to the first N results by relevance (used for crossref,
which has no Boolean search).

Writes data/raw_exports/<SEARCH_ID>_<SOURCE>_<date>.raw.json (raw API pages) and
.csv (flat records), and appends one row to data/search_log.csv.

Optional environment variables: OPENALEX_MAILTO, OPENALEX_API_KEY, S2_API_KEY.
"""
import argparse
import csv
import datetime as dt
import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
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


# --- source adapters: each returns (total_hits, raw_pages, records, filters_text) ---

def openalex(query, args):
    filters = [f"title_and_abstract.search:{query}"]
    extra = []
    if args.since:
        extra.append(f"from_publication_date:{args.since}")
    if args.until:
        extra.append(f"to_publication_date:{args.until}")
    # Page paging needs no API key (cursor paging does) and reaches 10,000 results.
    params = {"filter": ",".join(filters + extra), "per-page": 200, "page": 1,
              "select": "id,doi,title,publication_year,type,primary_location,authorships,"
                        "abstract_inverted_index,cited_by_count,keywords"}
    if os.environ.get("OPENALEX_MAILTO"):
        params["mailto"] = os.environ["OPENALEX_MAILTO"]
    if os.environ.get("OPENALEX_API_KEY"):
        params["api_key"] = os.environ["OPENALEX_API_KEY"]
    pages, rows, total = [], [], 0
    while True:
        page = fetch("https://api.openalex.org/works?" + urllib.parse.urlencode(params))
        pages.append(page)
        total = page["meta"]["count"]
        for w in page["results"]:
            inv = w.get("abstract_inverted_index") or {}
            abstract = " ".join(word for _, word in sorted((p, wd) for wd, ps in inv.items() for p in ps))
            loc = w.get("primary_location") or {}
            rows.append(record(
                source_record_id=w["id"].rsplit("/", 1)[-1], title=w.get("title"),
                authors=";".join(a["author"]["display_name"] for a in w.get("authorships") or []),
                year=w.get("publication_year"), venue=(loc.get("source") or {}).get("display_name"),
                work_type=w.get("type"), doi=w.get("doi"), url=loc.get("landing_page_url") or w["id"],
                abstract=abstract, keywords=";".join(k["display_name"] for k in w.get("keywords") or []),
                cited_by_count=w.get("cited_by_count")))
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


ADAPTERS = {"openalex": openalex, "semanticscholar": semanticscholar, "arxiv": arxiv,
            "europepmc": europepmc, "crossref": crossref, "doaj": doaj}
FIELDS = {"openalex": "title_abstract", "semanticscholar": "title_abstract", "arxiv": "all",
          "europepmc": "title_abstract", "crossref": "bibliographic", "doaj": "all"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", choices=sorted(ADAPTERS))
    ap.add_argument("search_id")
    ap.add_argument("query")
    ap.add_argument("--round", default="pilot", choices=["pilot", "main", "update"])
    ap.add_argument("--until", help="publication-date upper bound (search cut-off)")
    ap.add_argument("--since", help="publication-date lower bound (update searches)")
    ap.add_argument("--top", type=int, default=10_000, help="export at most N results")
    ap.add_argument("--run-by", default="R1")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    today = dt.date.today().isoformat()
    stem = f"{args.search_id}_{args.source}_{today}"
    raw_path, csv_path = EXPORTS / f"{stem}.raw.json", EXPORTS / f"{stem}.csv"
    if raw_path.exists() or csv_path.exists():
        raise SystemExit(f"{stem} already exists; raw exports are never overwritten.")

    total, pages, rows, filters = ADAPTERS[args.source](args.query, args)
    rows = rows[:args.top]

    EXPORTS.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    with SEARCH_LOG.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            args.search_id, today, args.source, "API", FIELDS[args.source], args.query,
            filters or "none", total, len(rows), csv_path.relative_to(ROOT).as_posix(),
            args.round, args.run_by, args.note])
    print(f"{args.search_id} {args.source}: {total} hits, {len(rows)} exported -> {csv_path.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
