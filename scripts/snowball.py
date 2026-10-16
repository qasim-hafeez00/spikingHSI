"""Backward and forward snowballing through OpenAlex (Protocol §7.5, Wohlin 2014).

Usage:
    python scripts/snowball.py --round 1 [--seeds auto | SH-0001,SH-0002,...] [--note TEXT]

Seeds: `auto` takes the papers R1 included (or marked maybe) at title/abstract or full text;
if R1 has not screened yet, it takes the pre-screening include/maybe suggestions as
provisional seeds (amendment A6). Explicit paper_ids can be given instead.

For each seed, the OpenAlex work is found by DOI (any alt_doi too), then by title
(similarity >= 0.93). Its reference list (backward) and the works citing it (forward) are
exported as two searches, B<round> and F<round>, in the common export schema (one row per
distinct work), logged in search_log.csv with round `snowball`, and one row per seed and
direction is appended to snowball_log.csv. Then rebuild with
    python scripts/build_records.py --round main,snowball

Needs OPENALEX_API_KEY (in .env) for the request volume.
"""
import argparse
import csv
import datetime as dt
import difflib
import json
import pathlib
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import search  # noqa: E402
from build_records import norm_title, read  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
API = "https://api.openalex.org/works"
SNOWBALL_COLUMNS = ["round", "seed_paper_id", "direction", "tool", "candidates", "new_records",
                    "new_included", "date", "run_by"]


def get(url_or_path, **params):
    """OpenAlex GET; None for a 404 (unknown DOI)."""
    url = url_or_path if url_or_path.startswith("http") else API + url_or_path
    try:
        return search.fetch(url + "?" + urllib.parse.urlencode(search.openalex_params(**params)))
    except SystemExit as e:
        if "HTTP 404" in str(e):
            return None
        raise


def auto_seeds():
    screening = read(DATA / "screening.csv")
    chosen = {s["paper_id"] for s in screening
              if s["round"] == "primary" and s["decision"] in ("include", "maybe")}
    if chosen:
        return sorted(chosen), "R1 include/maybe"
    suggestions = read(ROOT / "output" / "prescreen_suggestions.csv")
    return sorted(s["paper_id"] for s in suggestions if s["ai_suggestion"] in ("include", "maybe")), \
        "pre-screening include/maybe suggestions (provisional, A6)"


def resolve(paper):
    """OpenAlex work (id, referenced_works, cited_by_count) for a registry paper, or None."""
    select = "id,title,referenced_works,cited_by_count"
    for doi in filter(None, [paper["doi"]] + paper["alt_dois"].split(";")):
        w = get(f"/doi:{urllib.parse.quote(doi, safe='/')}", select=select)
        if w:
            return w, "doi"
    nt = norm_title(paper["title"])
    if len(nt) < 20:
        return None, ""
    hits = get("", search=paper["title"][:250], select=select, **{"per-page": 5}) or {"results": []}
    for w in hits["results"]:
        if difflib.SequenceMatcher(None, nt, norm_title(w.get("title"))).ratio() >= 0.93:
            return w, "title"
    return None, ""


def works_by_id(ids):
    rows = []
    ids = sorted(ids)
    for i in range(0, len(ids), 50):
        page = get("", filter="openalex_id:" + "|".join(ids[i:i + 50]), select=search.OPENALEX_SELECT,
                   **{"per-page": 50})
        rows += page["results"]
    return rows


def citing(wid):
    rows, page_no = [], 1
    while True:
        page = get("", filter=f"cites:{wid}", select=search.OPENALEX_SELECT, page=page_no, **{"per-page": 200})
        rows += page["results"]
        if not page["results"] or len(rows) >= page["meta"]["count"]:
            return rows
        page_no += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--seeds", default="auto")
    ap.add_argument("--run-by", default="R1")
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    today = dt.date.today().isoformat()
    for prefix in ("B", "F"):
        search.check_new(f"{prefix}{args.round}", "openalex")

    registry = {p["paper_id"]: p for p in read(DATA / "master_registry.csv")}
    if args.seeds == "auto":
        seed_ids, seed_rule = auto_seeds()
    else:
        seed_ids, seed_rule = [s.strip() for s in args.seeds.split(",")], "listed by R1"
    known_dois = {d for p in registry.values() for d in [p["doi"]] + p["alt_dois"].split(";") if d}
    known_titles = {norm_title(p["title"]) for p in registry.values()}

    def is_new(w):
        return search.clean_doi(w.get("doi")) not in known_dois and norm_title(w.get("title")) not in known_titles

    exports = {"backward": {}, "forward": {}}
    log, unresolved = [], []
    for n, pid in enumerate(seed_ids, 1):
        work, how = resolve(registry[pid])
        if not work:
            unresolved.append(pid)
            print(f"[{n}/{len(seed_ids)}] {pid}: not found in OpenAlex", flush=True)
            continue
        wid = work["id"].rsplit("/", 1)[-1]
        refs = works_by_id({r.rsplit("/", 1)[-1] for r in work.get("referenced_works") or []})
        cites = citing(wid) if work.get("cited_by_count") else []
        for direction, found in (("backward", refs), ("forward", cites)):
            for w in found:
                exports[direction].setdefault(w["id"], w)
            log.append({"round": args.round, "seed_paper_id": pid, "direction": direction, "tool": "openalex",
                        "candidates": len(found), "new_records": sum(map(is_new, found)), "new_included": "",
                        "date": today, "run_by": args.run_by})
        print(f"[{n}/{len(seed_ids)}] {pid} ({how} {wid}): {len(refs)} references, {len(cites)} citing",
              flush=True)

    ns = argparse.Namespace(round="snowball", run_by=args.run_by,
                            note=(args.note + "; " if args.note else "") + f"seeds: {seed_rule}"
                                 + (f"; not in OpenAlex: {';'.join(unresolved)}" if unresolved else ""))
    for direction, prefix in (("backward", "B"), ("forward", "F")):
        works = list(exports[direction].values())
        rows = [search.openalex_record(w) for w in works]
        query = f"{direction} snowballing round {args.round} from {len(seed_ids)} seeds: {';'.join(seed_ids)}"
        search.save_export(f"{prefix}{args.round}", "openalex", query, len(rows), works, rows, "", ns,
                           "API", "references" if direction == "backward" else "citations")

    path = DATA / "snowball_log.csv"
    with path.open("a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=SNOWBALL_COLUMNS).writerows(log)
    print(f"{len(seed_ids) - len(unresolved)}/{len(seed_ids)} seeds resolved; "
          f"{sum(r['new_records'] for r in log)} new-record hits (before dedup) -> rebuild the registry next")


if __name__ == "__main__":
    main()
