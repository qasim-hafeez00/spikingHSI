"""Run the searches that need a real browser, in a visible Chrome window shared with the reviewer.

Usage:
    python scripts/browser_search.py [--only S05a,S06a3,...] [--round main] [--run-by R1]

Opens Chrome (Playwright, persistent profile in .browser-profile/, so sign-ins and solved
challenges are remembered). When a site shows a CAPTCHA or "verify you are human" page,
the script waits for the reviewer to solve it in the window, then continues; it never
tries to solve or get past a challenge itself. The reviewer can use other tabs meanwhile.

Each search is saved and logged exactly like scripts/search.py (raw pages + flat CSV +
search_log.csv row). Queries are the frozen strings of protocol/search_strings.md.
"""
import argparse
import json
import random
import re
import sys
import time
import types
import urllib.parse

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import search  # noqa: E402  (shared parsers, record schema, export + logging)

PROFILE = str(search.ROOT / ".browser-profile")
WAIT_LIMIT = 900  # seconds to wait for a human to clear a challenge

SEARCHES = [
    # (search_id, source, fields, query)
    ("S05a", "sciencedirect", "title_abstract_keywords",
     '(spiking OR "spike-based" OR "spike-driven" OR "integrate-and-fire") AND (hyperspectral OR "hyper-spectral" OR "spectral imaging")'),
    ("S05b", "sciencedirect", "title_abstract_keywords",
     '(SNN OR neuromorphic OR spikformer) AND (hyperspectral OR "hyper-spectral" OR "spectral imaging")'),
    ("S11", "springer", "full_text", '"spiking neural" AND hyperspectral'),
    ("S07a", "dblp", "title", "spik hyperspectral"),
    ("S07b", "dblp", "title", "neuromorphic hyperspectral"),
    ("S07c", "dblp", "title", "SNN hyperspectral"),
    ("S06a3", "scholar", "full_text", '"spiking neural network" hyperspectral'),
    ("S06b3", "scholar", "full_text", "spiking hyperspectral classification"),
    ("S06c3", "scholar", "full_text", "neuromorphic hyperspectral"),
    ("S06d3", "scholar", "full_text", 'spikformer OR "spike-driven" hyperspectral'),
    # ACM last: its Cloudflare check may not clear in an automated browser.
    ("S12", "acm", "abstract", 'Abstract:(spiking OR neuromorphic OR "spike-driven") AND Abstract:(hyperspectral)'),
]
SCHOLAR_TOP = 300


def wait_for(page, ready, label):
    """Poll until ready(html) is true; tell the reviewer when a challenge is in the way."""
    t0, told = time.time(), False
    while time.time() - t0 < WAIT_LIMIT:
        try:
            html = page.content()
        except Exception:
            time.sleep(2)
            continue
        if ready(html):
            return html
        if not told:
            print(f"  [{label}] waiting - please solve the challenge in the browser window", flush=True)
            told = True
        time.sleep(3)
    raise TimeoutError(f"{label}: page never showed results within {WAIT_LIMIT}s")


def run_sciencedirect(page, query):
    pages, rows, offset, total = [], [], 0, 0
    while True:
        page.goto("https://www.sciencedirect.com/search?" +
                  urllib.parse.urlencode({"tak": query, "show": 100, "offset": offset}), wait_until="domcontentloaded")
        html = wait_for(page, lambda h: "result-list-title-link" in h or "No results found" in h
                        or re.search(r"\b0 results", h), "sciencedirect")
        pages.append(html)
        total = int((re.search(r"([\d,]+) results", html) or [0, "0"])[1].replace(",", ""))
        items = html.split('<li class="ResultItem')[1:]
        for it in items:
            sf = lambda p: search.strip_tags(search.first(p, it))
            date = sf(r'class="srctitle-date-fields">.*?</a></span><span>(.*?)</span>')
            rows.append(search.record(
                source_record_id=search.first(r'/science/article/pii/([A-Z0-9]+)', it),
                title=sf(r'class="anchor-text"><span>(.*?)</span></span></span></a></span></h2>'),
                authors=";".join(search.strip_tags(a) for a in re.findall(r'class="author text-xs">(.*?)</span>', it)),
                year=search.first(r"((?:19|20)\d{2})", date), venue=sf(r'subtype-srctitle-link.*?<span>([^<]*)</span>'),
                work_type=sf(r'class="article-type">(.*?)</span>'), doi=search.first(r'data-doi="([^"]+)"', it),
                url="https://www.sciencedirect.com/science/article/pii/" + search.first(r'/science/article/pii/([A-Z0-9]+)', it)))
        offset += 100
        if not items or offset >= total:
            return total, pages, rows, ""
        time.sleep(random.uniform(3, 6))


def run_springer(page, query):
    args = types.SimpleNamespace(since=None, until=None)
    pages, rows, page_no = [], [], 1
    while True:
        page.goto("https://link.springer.com/search?" +
                  urllib.parse.urlencode({"new-search": "true", "query": query, "page": page_no}),
                  wait_until="domcontentloaded")
        html = wait_for(page, lambda h: "search-result-item" in h or "No results" in h or "0 results" in h, "springer")
        pages.append(html)
        total, page_rows, n_items = search.parse_springer(html, args)
        rows.extend(page_rows)
        if not n_items or page_no * 20 >= total:
            return total, pages, rows, ""
        page_no += 1
        time.sleep(random.uniform(3, 6))


def run_acm(page, query):
    pages, rows, start, total = [], [], 0, 0
    while True:
        page.goto("https://dl.acm.org/action/doSearch?" + urllib.parse.urlencode(
            {"fillQuickSearch": "false", "target": "advanced", "expand": "dl", "AllField": query,
             "pageSize": 50, "startPage": start}), wait_until="domcontentloaded")
        html = wait_for(page, lambda h: "issue-item__title" in h or "search-result__no-result" in h
                        or "result__count" in h, "acm")
        pages.append(html)
        total = int((re.search(r'class="result__count">\s*([\d,]+)', html) or [0, "0"])[1].replace(",", ""))
        items = html.split('class="search__item')[1:]
        for it in items:
            doi = search.first(r'href="/doi/(10\.[^"?#]+)"', it)
            rows.append(search.record(
                source_record_id=doi,
                title=search.strip_tags(search.first(r'class="issue-item__title">(.*?)</h5>', it)
                                        or search.first(r'class="issue-item__title"[^>]*>(.*?)</h', it)),
                authors=";".join(search.strip_tags(a) for a in re.findall(r'<a href="/profile/[^"]*"[^>]*title="([^"]+)"', it)),
                year=search.first(r'class="bookPubDate[^"]*"[^>]*>[^<]*?((?:19|20)\d{2})', it)
                     or search.first(r"\b((?:19|20)\d{2})\b", search.strip_tags(search.first(r'class="issue-item__detail">(.*?)</div>', it))),
                venue=search.strip_tags(search.first(r'class="epub-section__title">(.*?)</span>', it)),
                work_type=search.strip_tags(search.first(r'class="issue-heading">(.*?)</div>', it)),
                doi=doi, url=f"https://dl.acm.org/doi/{doi}" if doi else "",
                abstract=search.strip_tags(search.first(r'class="issue-item__abstract[^"]*">(.*?)</div>', it))))
        start += 1
        if not items or start * 50 >= total:
            return total, pages, rows, ""
        time.sleep(random.uniform(3, 6))


def run_dblp(page, query):
    page.goto("https://dblp.org/search/publ/api?" + urllib.parse.urlencode({"q": query, "format": "json", "h": 1000}),
              wait_until="domcontentloaded")
    wait_for(page, lambda h: '"result"' in h, "dblp")
    data = json.loads(page.inner_text("body"))
    hits = data["result"]["hits"]
    rows = []
    for h in hits.get("hit", []):
        info = h["info"]
        authors = (info.get("authors") or {}).get("author", [])
        authors = authors if isinstance(authors, list) else [authors]
        rows.append(search.record(
            source_record_id=info.get("key"), title=info.get("title", "").rstrip("."),
            authors=";".join(a.get("text", "") for a in authors), year=info.get("year"), venue=info.get("venue"),
            work_type=info.get("type"), doi=info.get("doi"), url=info.get("ee") or info.get("url")))
    return int(hits.get("@total", len(rows))), [data], rows, ""


def run_scholar(page, query):
    pages, rows, start, total = [], [], 0, 0
    while start < SCHOLAR_TOP:
        page.goto("https://scholar.google.com/scholar?" + urllib.parse.urlencode({"q": query, "hl": "en", "start": start}),
                  wait_until="domcontentloaded")
        for attempt in range(6):
            html = wait_for(page, lambda h: ('class="gs_ri"' in h or "did not match any articles" in h
                                             or "perform the operation now" in h), "scholar")
            if "perform the operation now" not in html:
                break
            print("  [scholar] rate-limited ('try again later'); retrying in 2 minutes", flush=True)
            time.sleep(120)
            page.reload(wait_until="domcontentloaded")
        else:
            return total, pages, rows, f"PARTIAL: Scholar rate limit persisted at start={start}"
        pages.append(html)
        page_total, page_rows = search.parse_scholar(html)
        total = total or page_total
        rows.extend(page_rows)
        start += 10
        if not page_rows or start >= total:
            break
        time.sleep(random.uniform(10, 20))
    return total, pages, rows, f"top{SCHOLAR_TOP}"


RUNNERS = {"sciencedirect": run_sciencedirect, "springer": run_springer, "acm": run_acm,
           "dblp": run_dblp, "scholar": run_scholar}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated search ids")
    ap.add_argument("--round", default="main", choices=["pilot", "main", "update"])
    ap.add_argument("--run-by", default="R1")
    args = ap.parse_args()
    wanted = set(args.only.split(",")) if args.only else None
    todo = [s for s in SEARCHES if not wanted or s[0] in wanted]

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(PROFILE, channel="chrome", headless=False,
                                                   viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        for search_id, source, fields, query in todo:
            try:
                search.check_new(search_id, source)
            except SystemExit as e:
                print(f"{search_id}: skipped ({e})", flush=True)
                continue
            print(f"{search_id} {source}: {query}", flush=True)
            try:
                total, pages, rows, filters = RUNNERS[source](page, query)
            except Exception as e:  # keep going with the other searches; nothing is logged for this one
                print(f"{search_id}: FAILED, nothing logged ({e})", flush=True)
                continue
            log_args = types.SimpleNamespace(round=args.round, run_by=args.run_by,
                                             note="run in R1's browser (Playwright); challenges solved by R1")
            search.save_export(search_id, source, query, total, pages, rows, filters, log_args, "browser", fields)
        ctx.close()


if __name__ == "__main__":
    main()
