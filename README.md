# Spiking Neural Networks for Hyperspectral Imaging — Systematic Review

A systematic review (PRISMA 2020) of spiking models applied to hyperspectral imaging data.
The protocol is in [protocol/protocol.md](protocol/protocol.md).

## Layout

```
protocol/      protocol.md, search_strings.md, codebook.md, amendments.md
data/
  raw_exports/ untouched exports from each search (never edit)
  scoping/     scoping-search snapshots (Protocol §7.3)
  *.csv        linked tables, joined on paper_id (definitions in codebook.md)
scripts/       search, recall check, (later) dedup and master-sheet build
output/        generated files (master sheet, PRISMA counts, figures) — never hand-edit
```

## Rules

1. Raw exports are never edited. Every derived table must be reproducible from them.
2. A `paper_id` is permanent once assigned.
3. Every executed search is logged verbatim in `data/search_log.csv`.
4. Protocol changes after `protocol-v1.0` go into `protocol/amendments.md`.
5. PDFs live in Zotero, not in git.

## Order of work

- [x] Scope, RQs, eligibility, and the review type decided (draft protocol v0.1)
- [x] Scoping search (OpenAlex), recorded in Protocol §7.3
- [x] Seed set in `data/seeds.csv` (8 papers from an independent web-search pass)
- [x] Pilot of the scriptable sources: 8/8 seed recall, 577 unique papers, ~40 real candidates (output/pilot/)
- [ ] Pilot of the manual sources (IEEE, ScienceDirect, PoP/Scholar, dblp, Springer, ACM); search for existing reviews
- [ ] Freeze protocol (`git tag protocol-v1.0`), register on OSF
- [ ] Main searches D1–D7 → records.csv → deduplication → master_registry.csv
- [ ] Title/abstract screening, then intra-rater re-screen after 14 days
- [ ] Full-text screening (library requests for PDFs)
- [ ] Snowballing rounds until saturation
- [ ] Extraction, results, quality appraisal
- [ ] Update search before submission; synthesis and writing

## Running searches (exact strings in protocol/search_strings.md)

```
$env:OPENALEX_MAILTO="you@example.com"     # optional, PowerShell

# scriptable sources: openalex, semanticscholar, arxiv, europepmc, crossref, doaj
python scripts/search.py openalex S01 "<string>" --round main --until 2026-10-31

# manual sources (IEEE, ScienceDirect, Scholar/PoP, dblp, Springer, ACM): export, then
python scripts/import_export.py ieee S04 path\to\export.csv --query "<string>" --hits 57 --fields all_metadata --round main

# merge + deduplicate into data/ (pilot runs: --round pilot --out output/pilot)
python scripts/build_records.py --round main

# seed recall against any export or the registry
python scripts/check_seed_recall.py data/master_registry.csv
```

Requires Python 3.9+ and the standard library only.
