# Protocol amendments

Record changes made after the protocol is frozen (tag `protocol-v1.0`), one entry per change, using this format:

```
## A1 — YYYY-MM-DD
Section(s): §x.y
Change:
Reason:
Effect on already-processed records:
```

## A1 — 2026-10-16
Section(s): §1
Change: The placeholder "(To verify during the pilot: search for existing reviews)" was replaced with the result of that check. No dedicated SNN × HSI or SNN × remote-sensing review was found; the nearest related surveys are named.
Reason: §7.4 step 4 was completed only after the freeze.
Effect on already-processed records: none (wording of the rationale only).

## A2 — 2026-10-16
Section(s): §4.1 I6, §7.2
Change: Searches run on the cut-off date use no publication-date filter. The cut-off is applied as "records available in the source on the search date (2026-10-16)". S02 and the Crossref searches (S05c, S09a–d, S11c, S12c) were re-run without the filter as S02r, S05cr, S09ar–dr, S11cr, S12cr; the filtered runs are marked superseded in the search log and excluded from the build. Web sources (ScienceDirect, Springer, ACM, dblp, Scholar) are searched without a year filter.
Reason: In-press articles carry future issue dates (e.g., February 2027). The filter `publication date ≤ 2026-10-16` silently dropped them: the filtered Semantic Scholar run lost 12 records, 10 of them clearly relevant 2026 spiking-HSI papers.
Effect on already-processed records: none screened yet. The registry is rebuilt from the non-superseded runs. The filtered OpenAlex, arXiv, IEEE and Europe PMC runs (S01, S03, S04, S08) returned the same hit counts as unfiltered runs on the same day, so they stand.

## A3 — 2026-10-16
Section(s): §7.1
Change: The sources that block non-browser access were searched in a real browser instead of being left to manual export:
- ScienceDirect (S05a, S05b), SpringerLink (S11) and dblp (S07a–c): visible Chrome driven by Playwright (`scripts/browser_search.py`); R1 cleared any bot checks by hand.
- ACM DL (S12) and Google Scholar (S06a3–S06d3): R1's own Chrome through the Claude in Chrome extension; R1 passed the Cloudflare check. Scholar was paged at 8–15 s per page, top 300 per query, and the results HTML was saved as JSON (`scripts/import_scholar_browser.py`).

Earlier partial Scholar runs (S06a–c, S06a2–c2) are superseded by the complete S06x3 runs. The Crossref publisher-prefix searches (S05cr, S11cr, S12cr) are kept as additional searches.
Reason: Full coverage of the planned sources. No challenge was bypassed automatically; every CAPTCHA and bot check was cleared by R1.
Effect on already-processed records: none screened yet.

## A4 — 2026-10-16
Section(s): §7.1
Change: Five Crossref publisher-prefix searches were added (`spiking neural network hyperspectral`, top 100 by relevance, no date filter): SPIE 10.1117 (S13a), Taylor & Francis 10.1080 (S13b), Wiley 10.1002 (S13c), Optica 10.1364 (S13d), MDPI 10.3390 (S13e).
Reason: These publishers host key HSI and remote-sensing venues (J. Applied Remote Sensing and Proc. SPIE; Int. J. Remote Sensing and Remote Sensing Letters; Remote Sensing / Sensors). Their platforms were not searched directly, and one seed paper is from SPIE.
Effect on already-processed records: none screened yet.

## A5 — 2026-10-16
Section(s): §8.2, §8.3
Change: AI-assisted pre-screening of titles and abstracts. Suggestions only; R1 makes every screening decision.
1. **Abstract enrichment.** For records with no or short abstracts (< 300 characters), fuller abstracts were retrieved from OpenAlex (by DOI) and Semantic Scholar (by DOI) into `data/abstract_enrichment.csv`, with source and match recorded. 371 abstracts were added. Title matching for DOI-less records is pending (API limits).
2. **Rules** (`scripts/prescreen.py`, deterministic): E6 for non-articles by title pattern; E1 when no spiking/neuromorphic term appears; E2 when a spiking term appears but no hyperspectral term. Confidence is "high" on a full abstract and "medium" on a title or snippet only. Validation: a seeded random sample of 60 rule exclusions was read in full, and none was a spiking-HSI paper (0/60; 95% upper bound for the miss rate ≈ 5%).
3. **LLM reading.** Claude (Anthropic, model claude-opus-5-5) read every record the rules did not settle (337) and scanned the titles of the 395 records excluded by rule E2 on title or snippet only. It gave a suggestion, an exclusion code, a confidence and a one-line reason for each (`data/prescreen_llm.csv`). A reading overrides the rules.
4. **Use.** The suggestions appear in the screening sheet (`ai_*` columns) but are never imported as decisions. The intra-rater rescreen sheet is generated **without** suggestions, so it stays blind.

Open eligibility questions raised by pre-screening (decide before full text):
- Do pulse-coupled neural networks (PCNN) and spiking neural P systems meet I1?
- Does electron energy-loss spectrum imaging count as hyperspectral imaging (I2)?

Reason: Reduce the screening workload (2,115 records) while keeping every decision with R1, with the method reported as an automation tool under PRISMA 2020 item 8.
Effect on already-processed records: none screened yet.

## Pre-freeze decisions (for the record)
- 2026-10-16 — Conditional Phase 2 (spiking × broader remote sensing) dropped after the scoping search showed sufficient HSI volume (Protocol §5).
- 2026-10-16 — No publication-year lower bound (scoping found no relevant work before 2018).
- 2026-10-16 — Non-imaging 1-D spectra excluded (E2). Scoping found ~10 SNN-on-spectra papers out of 1,244 noisy hits.
- 2026-10-16 — Free sources only (no Scopus/WoS access). OpenAlex is the primary database.
- 2026-10-16 — Seed set built from an independent web-search pass (R1 had no prior papers). Seed recall of the combined pilot: 8/8.
- 2026-10-16 — Access routes fixed (Protocol §7.1). IEEE Xplore and Google Scholar are read through their web search endpoints. ScienceDirect, SpringerLink, ACM and dblp block non-browser access: they are searched manually, and Crossref publisher-prefix searches are run for them as well.
- 2026-10-16 — **Protocol frozen** (tag `protocol-v1.0`). Search cut-off date: 2026-10-16.
