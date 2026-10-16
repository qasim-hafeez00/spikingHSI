"""Make a screening sheet and import the decisions back into data/screening.csv.

Usage:
    python scripts/screening.py sheet  [--stage TA] [--reviewer R1] [--round primary]
    python scripts/screening.py import output/<sheet>.csv

`sheet` writes output/screening_<stage>_<reviewer>_<round>.csv (UTF-8 with BOM, so Excel
opens it correctly). It lists every paper that still needs a decision at that stage from
that reviewer:
  TA stage: all papers in master_registry.csv
  FT stage: papers whose latest TA decision is include or maybe
For a `rescreen` round, it lists a seeded random 20% sample of TA-screened papers, without
the earlier decisions (Protocol §8.3).

Fill in `decision` (include / exclude / maybe) and, for exclusions, `exclusion_code` (E1-E9),
then run `import`. Rows left blank are skipped. Imported rows are appended to screening.csv,
and master_registry.csv final_status is updated.
"""
import argparse
import csv
import datetime as dt
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SCREEN_COLUMNS = ["paper_id", "stage", "round", "reviewer", "decision", "exclusion_code", "date", "notes"]
SHEET_COLUMNS = ["paper_id", "decision", "exclusion_code", "notes", "ai_suggestion", "ai_code", "ai_confidence",
                 "ai_reason", "title", "abstract", "year", "venue", "venue_type", "doi", "url", "source_databases",
                 "ai_basis", "abstract_source", "stage", "round", "reviewer"]
OUTPUT = ROOT / "output"
DECISIONS = {"include", "exclude", "maybe"}
CODES = {f"E{i}" for i in range(1, 10)}
RESCREEN_SEED, RESCREEN_FRACTION = 20261016, 0.20


def read(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write(path, columns, rows, bom=False):
    with path.open("w", newline="", encoding="utf-8-sig" if bom else "utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def latest(screening, stage, round_="primary"):
    """Latest decision per paper at a stage (any reviewer, given round)."""
    out = {}
    for s in screening:
        if s["stage"] == stage and s["round"] == round_:
            out[s["paper_id"]] = s["decision"]
    return out


def with_prescreen(registry):
    """Add pre-screening suggestions (amendment A5) and enriched abstracts, if they exist.
    Suggestions are not shown in a rescreen round, which must be blind."""
    suggestions = {r["paper_id"]: r for r in read(OUTPUT / "prescreen_suggestions.csv")} \
        if (OUTPUT / "prescreen_suggestions.csv").exists() else {}
    enriched = {r["paper_id"]: r for r in read(DATA / "abstract_enrichment.csv")} \
        if (DATA / "abstract_enrichment.csv").exists() else {}
    out = []
    for p in registry:
        p = {**p, **suggestions.get(p["paper_id"], {}), "abstract_source": "registry"}
        e = enriched.get(p["paper_id"])
        if e and len(e["abstract"]) > len(p["abstract"]):
            p.update(abstract=e["abstract"], abstract_source=e["source"])
        out.append(p)
    return out


def make_sheet(args):
    registry = read(DATA / "master_registry.csv")
    if args.round != "rescreen":
        registry = with_prescreen(registry)
    screening = read(DATA / "screening.csv")
    done = {s["paper_id"] for s in screening
            if s["stage"] == args.stage and s["reviewer"] == args.reviewer and s["round"] == args.round}
    if args.round == "rescreen":
        screened = sorted(latest(screening, "TA"))
        pool = set(random.Random(RESCREEN_SEED).sample(screened, round(len(screened) * RESCREEN_FRACTION)))
    elif args.stage == "FT":
        pool = {p for p, d in latest(screening, "TA").items() if d in ("include", "maybe")}
    else:
        pool = {p["paper_id"] for p in registry}
    rows = [{**p, "decision": "", "exclusion_code": "", "notes": "", "stage": args.stage,
             "round": args.round, "reviewer": args.reviewer}
            for p in registry if p["paper_id"] in pool and p["paper_id"] not in done]
    # Likely includes and maybes first, then exclusions from least to most certain.
    order = {"include": 0, "maybe": 1, "": 2, "exclude": 3}
    conf = {"low": 0, "medium": 1, "high": 2, "": 1}
    rows.sort(key=lambda r: (order.get(r.get("ai_suggestion", ""), 2), conf.get(r.get("ai_confidence", ""), 1),
                             r["paper_id"]))
    out = ROOT / "output" / f"screening_{args.stage}_{args.reviewer}_{args.round}.csv"
    write(out, SHEET_COLUMNS, rows, bom=True)
    print(f"{len(rows)} papers to screen -> {out.relative_to(ROOT).as_posix()}")


def import_sheet(args):
    rows = read(pathlib.Path(args.sheet))
    today = dt.date.today().isoformat()
    new, problems = [], []
    for r in rows:
        decision = r["decision"].strip().lower()
        if not decision:
            continue
        code = r["exclusion_code"].strip().upper()
        if decision not in DECISIONS:
            problems.append(f"{r['paper_id']}: decision '{decision}'")
        elif decision == "exclude" and r["stage"] == "FT" and code not in CODES:
            problems.append(f"{r['paper_id']}: full-text exclusion needs a code E1-E9")
        elif decision == "maybe" and r["stage"] == "FT":
            problems.append(f"{r['paper_id']}: 'maybe' is not allowed at full text")
        elif code and code not in CODES:
            problems.append(f"{r['paper_id']}: exclusion code '{code}'")
        else:
            new.append({"paper_id": r["paper_id"], "stage": r["stage"], "round": r["round"],
                        "reviewer": r["reviewer"], "decision": decision, "exclusion_code": code,
                        "date": today, "notes": r["notes"]})
    if problems:
        raise SystemExit("Nothing imported; fix these rows first:\n  " + "\n  ".join(problems))

    screening = read(DATA / "screening.csv")
    keys = {(s["paper_id"], s["stage"], s["round"], s["reviewer"]) for s in screening}
    dupes = [n["paper_id"] for n in new if (n["paper_id"], n["stage"], n["round"], n["reviewer"]) in keys]
    if dupes:
        raise SystemExit(f"Nothing imported; already decided: {', '.join(dupes[:10])}")
    write(DATA / "screening.csv", SCREEN_COLUMNS, screening + new)

    # final_status follows the primary-round decisions.
    screening += new
    ta, ft = latest(screening, "TA"), latest(screening, "FT")
    registry = read(DATA / "master_registry.csv")
    for p in registry:
        pid = p["paper_id"]
        if pid in ft:
            p["final_status"] = "included" if ft[pid] == "include" else "excluded_FT"
        elif pid in ta:
            p["final_status"] = "excluded_TA" if ta[pid] == "exclude" else "pending"
    write(DATA / "master_registry.csv", list(registry[0].keys()), registry)
    print(f"Imported {len(new)} decisions into data/screening.csv")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet")
    s.add_argument("--stage", default="TA", choices=["TA", "FT"])
    s.add_argument("--reviewer", default="R1")
    s.add_argument("--round", default="primary", choices=["primary", "rescreen", "calibration"])
    i = sub.add_parser("import")
    i.add_argument("sheet")
    args = ap.parse_args()
    make_sheet(args) if args.cmd == "sheet" else import_sheet(args)


if __name__ == "__main__":
    main()
