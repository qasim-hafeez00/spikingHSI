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

## Pre-freeze decisions (for the record)
- 2026-10-16 — Conditional Phase 2 (spiking × broader remote sensing) dropped after the scoping search showed sufficient HSI volume (Protocol §5).
- 2026-10-16 — No publication-year lower bound (scoping found no relevant work before 2018).
- 2026-10-16 — Non-imaging 1-D spectra excluded (E2). Scoping found ~10 SNN-on-spectra papers out of 1,244 noisy hits.
- 2026-10-16 — Free sources only (no Scopus/WoS access). OpenAlex is the primary database.
- 2026-10-16 — Seed set built from an independent web-search pass (R1 had no prior papers). Seed recall of the combined pilot: 8/8.
- 2026-10-16 — Access routes fixed (Protocol §7.1). IEEE Xplore and Google Scholar are read through their web search endpoints. ScienceDirect, SpringerLink, ACM and dblp block non-browser access: they are searched manually, and Crossref publisher-prefix searches are run for them as well.
- 2026-10-16 — **Protocol frozen** (tag `protocol-v1.0`). Search cut-off date: 2026-10-16.
