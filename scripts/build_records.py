"""Merge logged search exports into records.csv, deduplicate, and update the registry.

Usage:
    python scripts/build_records.py [--round main] [--out data]

Reads every search_log.csv row of the given round(s) and its export CSV (common schema
written by search.py / import_export.py). Writes, under --out:
  records.csv            one row per exported record (rec_id = <search_id>-NNNN)
  deduplication_log.csv  every record merged into a paper first created by another record
  master_registry.csv    one row per unique paper; existing rows and paper_ids are kept,
                         only blank fields are filled, new papers are appended

Records are always clustered from scratch, in search-log order, so the output is
deterministic. Matching: DOI > exact normalized title > fuzzy title (ratio >= 0.90,
flagged for manual confirmation). Manual corrections go in data/dedup_overrides.csv:
  merge_into        put rec_id in the same paper as target_rec_id
  not_duplicate_of  keep rec_id out of the paper containing target_rec_id
A preprint merged with its published version takes the published metadata; the
preprint DOI moves to alt_dois.
"""
import argparse
import csv
import datetime as dt
import difflib
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FUZZY = 0.90
REGISTRY_COLUMNS = ["paper_id", "title", "authors", "year", "venue", "venue_type", "publisher", "doi",
                    "alt_dois", "url", "abstract", "keywords", "citation_count", "citation_date",
                    "source_databases", "found_via", "search_round", "venue_flag", "final_status",
                    "tier", "domain", "multimodal", "zotero_key", "first_rec_id", "notes"]
RECORD_COLUMNS = ["rec_id", "search_id", "source_db", "source_record_id", "title", "authors", "year",
                  "venue", "doi", "url", "abstract", "paper_id"]
DEDUP_COLUMNS = ["rec_id", "paper_id", "match_type", "similarity", "decided_by", "date", "notes"]
PREPRINT_VENUES = re.compile(r"arxiv|ssrn|research square|preprints\.org|techrxiv|biorxiv|medrxiv", re.I)


def read(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def norm_title(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def venue_type(rec):
    kind, venue, doi = (rec.get("work_type") or "").lower(), rec.get("venue") or "", rec["doi"]
    if "preprint" in kind or "posted-content" in kind or PREPRINT_VENUES.search(venue) \
            or doi.startswith("10.48550/") or doi.startswith("10.2139/ssrn"):
        return "preprint"
    if "proceedings" in kind or "conference" in kind or kind in ("conf", "cpaper") or \
            re.search(r"conference|proceedings|symposium|workshop|congress", venue, re.I):
        return "conference"
    if "journal" in kind or kind in ("article", "review", "letter") or venue:
        return "journal"
    return "other"


def load_records(rounds):
    """All exported records of the selected rounds, in search-log order."""
    out = []
    for log in read(DATA / "search_log.csv"):
        if log["round"] not in rounds or log["notes"].startswith("FAILED") or "superseded by" in log["notes"]:
            continue
        for n, rec in enumerate(read(ROOT / log["export_file"]), 1):
            rec = {**rec, "rec_id": f"{log['search_id']}-{n:04d}", "search_id": log["search_id"],
                   "source_db": log["database"], "round": log["round"], "log_date": log["date"],
                   "doi": (rec.get("doi") or "").lower().strip()}
            rec["nt"], rec["vt"] = norm_title(rec.get("title")), venue_type(rec)
            if rec["nt"] or rec["doi"]:
                out.append(rec)
    return out


def cluster(records):
    """Group records into papers. Returns {rec_id: cluster_no} and {rec_id: (match_type, sim)}."""
    by_doi, by_title, member, how = {}, {}, {}, {}
    clusters = []
    for rec in records:
        c, m, sim = None, "", ""
        if rec["doi"] and rec["doi"] in by_doi:
            c, m = by_doi[rec["doi"]], "doi"
        elif rec["nt"] in by_title:
            c, m = by_title[rec["nt"]], "title_exact"
        elif len(rec["nt"]) > 20:
            best, best_r = None, 0.0
            for t, cand in by_title.items():
                if abs(len(t) - len(rec["nt"])) > 0.2 * len(rec["nt"]):
                    continue
                sm = difflib.SequenceMatcher(None, rec["nt"], t, autojunk=False)
                # Cheap upper bounds first; ratio() is only computed for plausible matches.
                if sm.real_quick_ratio() < FUZZY or sm.quick_ratio() < FUZZY:
                    continue
                r = sm.ratio()
                if r > best_r:
                    best, best_r = cand, r
            if best_r >= FUZZY:
                c, m, sim = best, "title_fuzzy", f"{best_r:.3f}"
        if c is None:
            c = len(clusters)
            clusters.append([])
        clusters[c].append(rec)
        member[rec["rec_id"]], how[rec["rec_id"]] = c, (m, sim)
        if rec["doi"]:
            by_doi.setdefault(rec["doi"], c)
        if rec["nt"]:
            by_title.setdefault(rec["nt"], c)
    return member, how


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", default="main", help="search round(s) to include, comma-separated")
    ap.add_argument("--out", default="data")
    args = ap.parse_args()
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()

    records = load_records(set(args.round.split(",")))
    member, how = cluster(records)

    # Manual overrides, applied after automatic clustering.
    next_c = max(member.values(), default=-1) + 1
    for ov in read(DATA / "dedup_overrides.csv"):
        rid, target = ov["rec_id"], ov.get("target_rec_id", "")
        if rid not in member or target not in member:
            continue
        if ov["action"] == "merge_into":
            member[rid], how[rid] = member[target], ("manual", "")
        elif ov["action"] == "not_duplicate_of" and member[rid] == member[target]:
            member[rid], how[rid] = next_c, ("", "")
            next_c += 1

    groups = {}
    for rec in records:
        groups.setdefault(member[rec["rec_id"]], []).append(rec)

    # Map clusters onto existing paper_ids (via first_rec_id), then mint new ids.
    registry = read(out / "master_registry.csv")
    by_first = {p["first_rec_id"]: p for p in registry if p.get("first_rec_id")}
    papers = {p["paper_id"]: p for p in registry}
    next_id = max([int(pid.split("-")[1]) for pid in papers] or [0]) + 1
    used = set()
    dedup, rec_paper = [], {}
    for c in sorted(groups):
        recs = groups[c]
        paper = next((by_first[r["rec_id"]] for r in recs
                      if r["rec_id"] in by_first and by_first[r["rec_id"]]["paper_id"] not in used), None)
        if paper is None:
            first = recs[0]
            paper = {col: "" for col in REGISTRY_COLUMNS}
            paper.update(paper_id=f"SH-{next_id:04d}", first_rec_id=first["rec_id"], venue_flag="ok",
                         final_status="pending", search_round=first["round"],
                         found_via={"B": "backward", "F": "forward"}.get(first["search_id"][0],
                                   "seed" if first["source_db"] == "seed" else "database"))
            next_id += 1
            registry.append(paper)
        used.add(paper["paper_id"])

        # Published records outrank preprints for the paper's metadata.
        primary = next((r for r in recs if r["vt"] in ("journal", "conference")), recs[0])
        if paper["venue_type"] == "preprint" and primary["vt"] != "preprint":
            for field in ("title", "venue", "year", "doi", "url"):
                paper[field] = ""
            paper["venue_type"] = ""
        for rec in [primary] + recs:
            for field in ("title", "authors", "year", "venue", "doi", "url", "abstract", "keywords"):
                if not paper[field] and rec.get(field):
                    paper[field] = rec[field]
        paper["venue_type"] = paper["venue_type"] or primary["vt"]
        dois = {r["doi"] for r in recs if r["doi"]} | set(filter(None, paper["alt_dois"].split(";")))
        paper["alt_dois"] = ";".join(sorted(dois - {paper["doi"]}))
        paper["source_databases"] = ";".join(sorted(
            set(filter(None, paper["source_databases"].split(";"))) | {r["source_db"] for r in recs}))
        oa = [r for r in recs if r["source_db"] == "openalex" and r.get("cited_by_count")]
        if oa:
            paper["citation_count"], paper["citation_date"] = oa[-1]["cited_by_count"], oa[-1]["log_date"]

        for rec in recs:
            rec_paper[rec["rec_id"]] = paper["paper_id"]
            if rec["rec_id"] == paper["first_rec_id"]:
                continue
            m, sim = how[rec["rec_id"]]
            if m != "manual" and rec["vt"] != paper["venue_type"] and "preprint" in (rec["vt"], paper["venue_type"]) \
                    and rec["doi"] != paper["doi"]:
                m = "version_link"
            dedup.append({"rec_id": rec["rec_id"], "paper_id": paper["paper_id"], "match_type": m or "manual",
                          "similarity": sim, "decided_by": "manual" if m == "manual" else "script",
                          "date": today, "notes": "CONFIRM MANUALLY" if m == "title_fuzzy" else ""})

    write(out / "records.csv", RECORD_COLUMNS, [{**r, "paper_id": rec_paper[r["rec_id"]]} for r in records])
    write(out / "deduplication_log.csv", DEDUP_COLUMNS, dedup)
    write(out / "master_registry.csv", REGISTRY_COLUMNS, registry)
    fuzzy = sum(d["match_type"] == "title_fuzzy" for d in dedup)
    print(f"{len(records)} records -> {len(used)} unique papers ({len(dedup)} merged; "
          f"{fuzzy} fuzzy matches to confirm) in {out.relative_to(ROOT).as_posix()}/")


if __name__ == "__main__":
    main()
