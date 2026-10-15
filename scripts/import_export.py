"""Import a manually downloaded search export into the common schema and log the search.

Usage:
    python scripts/import_export.py SOURCE SEARCH_ID FILE --query "..." --hits N
                                    [--fields all_metadata] [--interface web]
                                    [--round pilot|main|update] [--run-by R1] [--note TEXT]

SOURCE: ieee | sciencedirect | springer | acm | scholar | dblp | other
FILE formats: .csv (IEEE Xplore, SpringerLink, Publish or Perish), .ris, .bib, .json (dblp API).
The original file is copied unchanged to data/raw_exports/<SEARCH_ID>_<SOURCE>_<date>.orig.<ext>,
the converted records go to ...csv, and one row is appended to data/search_log.csv.
"""
import argparse
import csv
import datetime as dt
import json
import pathlib
import re
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "data" / "raw_exports"
SEARCH_LOG = ROOT / "data" / "search_log.csv"
EXPORT_COLUMNS = ["source_record_id", "title", "authors", "year", "venue", "work_type",
                  "doi", "url", "abstract", "keywords", "cited_by_count"]

# Column names used by IEEE Xplore, SpringerLink and Publish or Perish CSV exports.
CSV_FIELDS = {
    "title": ["document title", "item title", "title"],
    "authors": ["authors", "author"],
    "year": ["publication year", "year"],
    "venue": ["publication title", "source", "journal"],
    "work_type": ["content type", "type", "document identifier"],
    "doi": ["doi", "item doi"],
    "url": ["pdf link", "url", "articleurl", "article url"],
    "abstract": ["abstract"],
    "keywords": ["author keywords", "keywords"],
    "cited_by_count": ["article citation count", "cites"],
}
RIS_FIELDS = {"TI": "title", "T1": "title", "AU": "authors", "A1": "authors", "PY": "year",
              "Y1": "year", "DA": "year", "JO": "venue", "T2": "venue", "JF": "venue", "BT": "venue",
              "DO": "doi", "UR": "url", "AB": "abstract", "N2": "abstract", "KW": "keywords", "TY": "work_type"}


def clean(row):
    out = {c: " ".join(str(row.get(c) or "").split()) for c in EXPORT_COLUMNS}
    out["doi"] = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", out["doi"].lower())
    m = re.search(r"\d{4}", out["year"])
    out["year"] = m.group(0) if m else ""
    return out


def from_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        lower = {h.lower().strip(): h for h in reader.fieldnames or []}
        cols = {k: next((lower[c] for c in cands if c in lower), None) for k, cands in CSV_FIELDS.items()}
        return [{k: (r.get(c) or "") if c else "" for k, c in cols.items()} for r in reader]


def from_ris(path):
    rows, cur = [], {}
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        m = re.match(r"^([A-Z][A-Z0-9])  - ?(.*)$", line)
        if not m:
            continue
        tag, val = m.groups()
        if tag == "ER":
            rows.append(cur)
            cur = {}
        elif tag in RIS_FIELDS:
            key = RIS_FIELDS[tag]
            if key in ("authors", "keywords") and cur.get(key):
                cur[key] += ";" + val
            elif not cur.get(key):
                cur[key] = val
    return rows


def from_bib(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    rows = []
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,]+),(.*?)\n\}", text, re.S):
        kind, key, body = m.groups()
        fields = {k.lower(): re.sub(r"[{}]", "", v).strip()
                  for k, v in re.findall(r"(\w+)\s*=\s*[{\"](.*?)[}\"]\s*,?\s*\n", body + "\n", re.S)}
        rows.append({"source_record_id": key, "title": fields.get("title"),
                     "authors": ";".join(a.strip() for a in fields.get("author", "").split(" and ")),
                     "year": fields.get("year"), "venue": fields.get("journal") or fields.get("booktitle"),
                     "work_type": kind, "doi": fields.get("doi"), "url": fields.get("url"),
                     "abstract": fields.get("abstract"), "keywords": fields.get("keywords", "").replace(",", ";")})
    return rows


def from_dblp_json(path):
    hits = json.loads(path.read_text(encoding="utf-8"))["result"]["hits"].get("hit", [])
    rows = []
    for h in hits:
        info = h["info"]
        authors = (info.get("authors") or {}).get("author", [])
        authors = authors if isinstance(authors, list) else [authors]
        rows.append({"source_record_id": info.get("key"), "title": info.get("title", "").rstrip("."),
                     "authors": ";".join(a.get("text", "") for a in authors), "year": info.get("year"),
                     "venue": info.get("venue"), "work_type": info.get("type"), "doi": info.get("doi"),
                     "url": info.get("ee") or info.get("url")})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", choices=["ieee", "sciencedirect", "springer", "acm", "scholar", "dblp", "other"])
    ap.add_argument("search_id")
    ap.add_argument("file", type=pathlib.Path)
    ap.add_argument("--query", required=True, help="the exact query string as typed")
    ap.add_argument("--hits", required=True, help="hit count shown by the source")
    ap.add_argument("--fields", default="")
    ap.add_argument("--filters", default="none")
    ap.add_argument("--interface", default="web")
    ap.add_argument("--round", default="pilot", choices=["pilot", "main", "update"])
    ap.add_argument("--run-by", default="R1")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    ext = args.file.suffix.lower()
    parser = {".csv": from_csv, ".ris": from_ris, ".bib": from_bib, ".json": from_dblp_json}.get(ext)
    if parser is None:
        raise SystemExit(f"Unsupported file type {ext}; export as CSV, RIS, BibTeX or dblp JSON.")
    rows = [clean(r) for r in parser(args.file)]
    rows = [r for r in rows if r["title"] or r["doi"]]

    today = dt.date.today().isoformat()
    stem = f"{args.search_id}_{args.source}_{today}"
    orig, csv_path = EXPORTS / f"{stem}.orig{ext}", EXPORTS / f"{stem}.csv"
    if orig.exists() or csv_path.exists():
        raise SystemExit(f"{stem} already exists; raw exports are never overwritten.")
    shutil.copy2(args.file, orig)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    with SEARCH_LOG.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([args.search_id, today, args.source, args.interface, args.fields, args.query,
                                args.filters, args.hits, len(rows), csv_path.relative_to(ROOT).as_posix(),
                                args.round, args.run_by, args.note])
    print(f"{args.search_id} {args.source}: {len(rows)} records imported -> {csv_path.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
