"""Fetch fuller abstracts for registry papers whose abstract is missing or a short snippet.

Usage:
    python scripts/enrich_abstracts.py [--min-length 300]

Writes data/abstract_enrichment.csv (paper_id, source, matched_id, matched_title,
similarity, abstract, date). The registry is not modified; the screening sheet shows
the longer of the registry abstract and the enriched one. Papers already in the
enrichment file are skipped, and results are saved after every step, so re-running
only fills the remaining gaps.

Order: OpenAlex by DOI (50 per request) -> Semantic Scholar batch by DOI (covers
publishers whose abstracts OpenAlex does not carry) -> title search for papers without
a DOI (OpenAlex, or Semantic Scholar once the OpenAlex budget is used up), accepted
only at title similarity >= 0.93 or an exact prefix match for titles Scholar truncated.

Optional environment variables: OPENALEX_MAILTO, OPENALEX_API_KEY, S2_API_KEY.
"""
import argparse
import csv
import datetime as dt
import difflib
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build_records import norm_title, read  # noqa: E402
import search  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "abstract_enrichment.csv"
COLUMNS = ["paper_id", "source", "matched_id", "matched_title", "similarity", "abstract", "date"]
OA_SELECT = "id,doi,title,abstract_inverted_index"


class BudgetExhausted(Exception):
    pass


def oa_abstract(work):
    inv = work.get("abstract_inverted_index") or {}
    return " ".join(w for _, w in sorted((p, w) for w, ps in inv.items() for p in ps))


def oa_get(params):
    params = {**params, "select": OA_SELECT}
    for env, key in (("OPENALEX_MAILTO", "mailto"), ("OPENALEX_API_KEY", "api_key")):
        if os.environ.get(env):
            params[key] = os.environ[env]
    try:
        return search.fetch("https://api.openalex.org/works?" + urllib.parse.urlencode(params), pause=0.15)
    except SystemExit as e:
        if "429" in str(e):
            raise BudgetExhausted(str(e)[:120])
        raise


def s2_request(url, body=None):
    headers = {"User-Agent": search.USER_AGENT}
    if os.environ.get("S2_API_KEY"):
        headers["x-api-key"] = os.environ["S2_API_KEY"]
    if body is not None:
        headers["Content-Type"] = "application/json"
    for attempt in range(7):
        try:
            req = urllib.request.Request(url, data=body, headers=headers)
            return json.load(urllib.request.urlopen(req, timeout=120))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code != 429 or attempt == 6:
                raise
            time.sleep(3 * 2 ** attempt)


def title_match(ours, theirs):
    a, b = norm_title(ours.rstrip(".… ").replace("…", "")), norm_title(theirs)
    if not a or not b:
        return 0.0
    if ("…" in ours or "..." in ours) and len(a) >= 30 and b.startswith(a):
        return 1.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def save(found, today):
    rows = read(OUT)
    have = {r["paper_id"] for r in rows}
    rows += [{"paper_id": pid, "source": s, "matched_id": mid, "matched_title": mt, "similarity": sim,
              "abstract": " ".join(text.split()), "date": today}
             for pid, (s, mid, mt, sim, text) in sorted(found.items()) if pid not in have]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-length", type=int, default=300)
    args = ap.parse_args()
    today = dt.date.today().isoformat()

    done = {r["paper_id"] for r in read(OUT)}
    todo = [p for p in read(ROOT / "data" / "master_registry.csv")
            if len(p["abstract"]) < args.min_length and p["paper_id"] not in done]
    found = {}

    # 1. OpenAlex by DOI, 50 per request.
    by_doi = {p["doi"].lower(): p for p in todo if p["doi"]}
    dois = list(by_doi)
    for i in range(0, len(dois), 50):
        chunk = dois[i:i + 50]
        try:
            page = oa_get({"filter": "doi:" + "|".join(chunk), "per-page": 50})
        except BudgetExhausted as e:
            print(f"OpenAlex budget exhausted, skipping the rest of the DOI step: {e}")
            break
        for w in page["results"]:
            doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
            text = oa_abstract(w)
            if doi in by_doi and len(text) > len(by_doi[doi]["abstract"]):
                found[by_doi[doi]["paper_id"]] = ("openalex_doi", w["id"].rsplit("/", 1)[-1], w.get("title") or "", "1.000", text)
    print(f"OpenAlex by DOI: {len(found)} of {len(dois)}", flush=True)
    save(found, today)

    # 2. Semantic Scholar batch by DOI for the rest.
    rest = [d for d in dois if by_doi[d]["paper_id"] not in found]
    s2 = 0
    for i in range(0, len(rest), 400):
        chunk = rest[i:i + 400]
        body = json.dumps({"ids": [f"DOI:{d}" for d in chunk]}).encode()
        result = s2_request("https://api.semanticscholar.org/graph/v1/paper/batch?fields=title,abstract", body) or []
        for doi, r in zip(chunk, result):
            if r and r.get("abstract") and len(r["abstract"]) > len(by_doi[doi]["abstract"]):
                found[by_doi[doi]["paper_id"]] = ("semanticscholar_doi", r.get("paperId", ""), r.get("title") or "", "1.000", r["abstract"])
                s2 += 1
        time.sleep(2)
    print(f"Semantic Scholar by DOI: {s2} of {len(rest)}", flush=True)
    save(found, today)

    # 3. Title search for papers without a DOI.
    no_doi = [p for p in todo if not p["doi"] and len(norm_title(p["title"])) >= 20]
    by_title, oa_ok = 0, True
    for n, p in enumerate(no_doi, 1):
        query = p["title"].replace("…", " ").replace("...", " ")
        query = " ".join("".join(ch if ch.isalnum() or ch.isspace() else " " for ch in query).split()[:30])
        candidates = []
        if oa_ok:
            try:
                candidates = [("openalex_title", w["id"].rsplit("/", 1)[-1], w.get("title") or "", oa_abstract(w))
                              for w in oa_get({"search": query, "per-page": 5})["results"]]
            except BudgetExhausted as e:
                print(f"OpenAlex budget exhausted, using Semantic Scholar for titles: {e}", flush=True)
                oa_ok = False
        if not oa_ok:
            try:
                r = s2_request("https://api.semanticscholar.org/graph/v1/paper/search/match?" +
                               urllib.parse.urlencode({"query": query, "fields": "title,abstract"}))
            except urllib.error.HTTPError as e:
                print(f"Semantic Scholar rate limit persisted ({e.code}); stopping the title step at {n}/{len(no_doi)}. "
                      "Re-run later or with OPENALEX_API_KEY / S2_API_KEY to continue.", flush=True)
                break
            time.sleep(1.1)
            candidates = [("semanticscholar_title", d.get("paperId", ""), d.get("title") or "", d.get("abstract") or "")
                          for d in (r or {}).get("data", [])]
        best, best_r = None, 0.0
        for c in candidates:
            r = title_match(p["title"], c[2])
            if r > best_r:
                best, best_r = c, r
        if best and best_r >= 0.93 and len(best[3]) > len(p["abstract"]):
            found[p["paper_id"]] = (best[0], best[1], best[2], f"{best_r:.3f}", best[3])
            by_title += 1
        if n % 50 == 0:
            save(found, today)
            print(f"  titles: {n}/{len(no_doi)} checked, {by_title} matched", flush=True)
    save(found, today)
    print(f"By title: {by_title} of {len(no_doi)}")
    print(f"{len(found)} abstracts added -> {OUT.relative_to(ROOT).as_posix()} ({len(todo)} papers needed one)")


if __name__ == "__main__":
    main()
