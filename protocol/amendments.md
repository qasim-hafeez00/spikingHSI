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

## Pre-freeze decisions (for the record)
- 2026-10-16 — Conditional Phase 2 (spiking × broader remote sensing) dropped after the scoping search showed sufficient HSI volume (Protocol §5).
- 2026-10-16 — No publication-year lower bound (scoping found no relevant work before 2018).
- 2026-10-16 — Non-imaging 1-D spectra excluded (E2). Scoping found ~10 SNN-on-spectra papers out of 1,244 noisy hits.
- 2026-10-16 — Free sources only (no Scopus/WoS access). OpenAlex is the primary database.
- 2026-10-16 — Seed set built from an independent web-search pass (R1 had no prior papers). Seed recall of the combined pilot: 8/8.
- 2026-10-16 — Access routes fixed (Protocol §7.1). IEEE Xplore and Google Scholar are read through their web search endpoints. ScienceDirect, SpringerLink, ACM and dblp block non-browser access: they are searched manually, and Crossref publisher-prefix searches are run for them as well.
- 2026-10-16 — **Protocol frozen** (tag `protocol-v1.0`). Search cut-off date: 2026-10-16.
