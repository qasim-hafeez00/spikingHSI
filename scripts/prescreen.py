"""Title/abstract PRE-screening: suggestions only; R1 makes every decision (amendment A5).

Usage:
    python scripts/prescreen.py queue    # write output/prescreen_queue.csv: papers that need a reading
    python scripts/prescreen.py build    # merge rules + data/prescreen_llm.csv -> suggestions,
                                         # exclusion list, and a screening sheet with ai_* columns

Two layers:
1. Deterministic rules decide only clear cases, with a confidence label:
   - E6  title is a peer-review letter, supplement, dataset, erratum, front matter, ...
   - E1  no spiking / neuromorphic term anywhere in title + abstract
   - E2  a spiking term, but no hyperspectral term anywhere in title + abstract
   "high" = judged on a full abstract (>= 300 chars); "medium" = title or snippet only.
2. Every other paper (spiking AND hyperspectral signal, or an ambiguous term such as
   SNN, brain-inspired, pulse-coupled, event-based, memristive) is read by Claude, whose
   suggestion and one-line reason are stored in data/prescreen_llm.csv.

Abstracts: the longer of the registry abstract and data/abstract_enrichment.csv.
"""
import csv
import pathlib
import random
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, OUTPUT = ROOT / "data", ROOT / "output"
LONG = 300
SPIKE = re.compile(r"spiking|spike[- ]?(?:based|driven|train|timing|coding|encod|count)|integrate[- ]and[- ]fire|"
                   r"\bp?lif\b|\bsnns?\b|neuromorphic|spikformer|spikingformer|izhikevich|\bstdp\b", re.I)
AMBIGUOUS = re.compile(r"brain[- ]inspired|pulse[- ]coupled|\bpcnn\b|event[- ]based|event camera|dynamic vision sensor|"
                       r"memristi|bio[- ]?inspired neur", re.I)
HSI = re.compile(r"hyperspectra|hyper-spectral|imaging spectro|spectral imag|\bhsi\b|indian pines|pavia|salinas|"
                 r"whu-hi|houston ?20|spectral[- –]spatial|spatial[- –]spectral", re.I)
E6_TITLE = re.compile(r"^\s*(decision letter|review for|author response|reply to|response to|supplementary|supplemental|"
                      r"data for|dataset for|table \d|figure \d|correction|erratum|corrigendum|retraction|front matter|"
                      r"back matter|cover image|index\b|contents\b|poster session|keynote|editorial|preface|foreword|"
                      r"3d mechanical design files|pcb design files|3d cad models)", re.I)
SUGGEST_COLUMNS = ["paper_id", "ai_suggestion", "ai_code", "ai_confidence", "ai_basis", "ai_reason"]
EXCL_COLUMNS = ["paper_id", "title", "year", "venue", "ai_code", "ai_confidence", "ai_basis", "ai_reason"]
CODE_TEXT = {"E1": "no spiking model", "E2": "not hyperspectral imaging data", "E3": "neuromorphic hardware/sensor without a spiking model on HSI",
             "E4": "no empirical evaluation on HSI", "E5": "secondary study (review/survey)", "E6": "ineligible publication type",
             "E7": "non-English", "E8": "full text unavailable", "E9": "duplicate/superseded version"}


def read(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write(path, columns, rows, bom=False):
    with path.open("w", newline="", encoding="utf-8-sig" if bom else "utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def papers():
    enriched = {r["paper_id"]: r for r in read(DATA / "abstract_enrichment.csv")}
    out = []
    for p in read(DATA / "master_registry.csv"):
        e = enriched.get(p["paper_id"])
        if e and len(e["abstract"]) > len(p["abstract"]):
            p = {**p, "abstract": e["abstract"], "abstract_source": e["source"]}
        else:
            p = {**p, "abstract_source": "registry"}
        out.append(p)
    return out


def rule(p):
    """Return (suggestion, code, confidence, reason) for clear cases, or None if it needs reading."""
    text = f"{p['title']} {p['abstract']}"
    full = len(p["abstract"]) >= LONG
    conf, basis = ("high", "full abstract") if full else ("medium", "title/snippet only")
    if E6_TITLE.search(p["title"]):
        return "exclude", "E6", "high", "title", "not a research article (review letter, supplement, dataset, erratum or similar)"
    has_spike, has_hsi = bool(SPIKE.search(text)), bool(HSI.search(text))
    if has_spike and not has_hsi:
        return "exclude", "E2", conf, basis, "spiking model, but no hyperspectral data mentioned"
    if AMBIGUOUS.search(text) or (has_spike and has_hsi):
        return None
    return "exclude", "E1", conf, basis, "no spiking or neuromorphic model mentioned"


def queue():
    rows = []
    for p in papers():
        if rule(p) is None:
            rows.append({"paper_id": p["paper_id"], "year": p["year"], "title": p["title"],
                         "abstract": p["abstract"][:900], "venue": p["venue"]})
    write(OUTPUT / "prescreen_queue.csv", ["paper_id", "year", "title", "venue", "abstract"], rows)
    print(f"{len(rows)} papers need reading -> output/prescreen_queue.csv")


def build():
    llm = {r["paper_id"]: r for r in read(DATA / "prescreen_llm.csv")}
    suggestions, missing = [], []
    by_id = {}
    for p in papers():
        by_id[p["paper_id"]] = p
        r = rule(p)
        if p["paper_id"] in llm:  # a reading always overrides the rules
            j = llm[p["paper_id"]]
            suggestions.append({"paper_id": p["paper_id"], "ai_suggestion": j["suggestion"], "ai_code": j["code"],
                                "ai_confidence": j.get("confidence", ""), "ai_basis": "Claude (title + abstract)",
                                "ai_reason": j["reason"]})
        elif r is not None:
            s, code, conf, basis, reason = r
            suggestions.append({"paper_id": p["paper_id"], "ai_suggestion": s, "ai_code": code,
                                "ai_confidence": conf, "ai_basis": f"rule ({basis})", "ai_reason": reason})
        else:
            missing.append(p["paper_id"])
            suggestions.append({"paper_id": p["paper_id"], "ai_suggestion": "", "ai_code": "", "ai_confidence": "",
                                "ai_basis": "not yet read", "ai_reason": ""})
    write(OUTPUT / "prescreen_suggestions.csv", SUGGEST_COLUMNS, suggestions)

    excl = [{**by_id[s["paper_id"]], **s} for s in suggestions if s["ai_suggestion"] == "exclude"]
    excl.sort(key=lambda r: (r["ai_code"], r["ai_confidence"] != "high", r["paper_id"]))
    write(OUTPUT / "prescreen_exclusion_list.csv", EXCL_COLUMNS, excl, bom=True)

    counts = {}
    for s in suggestions:
        key = (s["ai_suggestion"] or "unread", s["ai_code"], s["ai_basis"].split(" (")[0])
        counts[key] = counts.get(key, 0) + 1
    for k in sorted(counts):
        print(f"  {k[0]:8} {k[1]:3} {k[2]:8} {counts[k]:5}")
    print(f"{len(excl)} suggested exclusions -> output/prescreen_exclusion_list.csv")
    if missing:
        print(f"WARNING: {len(missing)} papers not yet read: {', '.join(missing[:10])}...")


def validation_sample(n=60, seed=20261016):
    """Seeded sample of rule-based exclusions for checking the rules by reading (reported in the paper)."""
    ruled = [p for p in papers() if (rule(p) or ("",))[0] == "exclude"]
    sample = random.Random(seed).sample(ruled, min(n, len(ruled)))
    write(OUTPUT / "prescreen_rule_validation_sample.csv", ["paper_id", "title", "abstract"],
          [{"paper_id": p["paper_id"], "title": p["title"], "abstract": p["abstract"][:600]} for p in sample])
    print(f"{len(sample)} rule exclusions sampled -> output/prescreen_rule_validation_sample.csv")


if __name__ == "__main__":
    {"queue": queue, "build": build, "validate": validation_sample}[sys.argv[1]]()
