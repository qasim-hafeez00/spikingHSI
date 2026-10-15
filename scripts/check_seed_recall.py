"""Report which seed papers are retrieved by one or more search exports.

Usage:
    python scripts/check_seed_recall.py data/raw_exports/S01_openalex_2026-10-20.csv [more.csv ...]

Seeds come from data/seeds.csv. Matching is by DOI first, then by normalized title.
Export CSVs need `title` and `doi` columns.
"""
import csv
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def norm_title(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def norm_doi(d):
    return (d or "").lower().replace("https://doi.org/", "").strip()


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main(export_paths):
    seeds = read(ROOT / "data" / "seeds.csv")
    if not seeds:
        raise SystemExit("data/seeds.csv is empty.")
    found_by = {s["seed_id"]: [] for s in seeds}
    for path in export_paths:
        rows = read(path)
        dois = {norm_doi(r.get("doi")) for r in rows} - {""}
        titles = {norm_title(r.get("title")) for r in rows} - {""}
        for s in seeds:
            if norm_doi(s["doi"]) in dois or norm_title(s["title"]) in titles:
                found_by[s["seed_id"]].append(pathlib.Path(path).stem)

    hit = sum(bool(v) for v in found_by.values())
    print(f"Recall: {hit}/{len(seeds)} seeds retrieved\n")
    for s in seeds:
        sources = ", ".join(found_by[s["seed_id"]]) or "MISSED"
        print(f"{s['seed_id']:>6}  {sources:<40}  {s['title'][:80]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1:])
