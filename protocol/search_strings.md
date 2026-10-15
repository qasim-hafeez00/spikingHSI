# Search strings — v1.0 (FROZEN 2026-10-16 with protocol-v1.0; cut-off date 2026-10-16)

Every executed string is copied verbatim into `data/search_log.csv`. The string in the log, not this file, is the record of what was actually run.

## Concept blocks

**Spiking block (S):**
`spiking`, `"spike-based"`, `"spike-driven"`, `"integrate-and-fire"`, `spikformer`, `spikingformer`, `SNN`, `SNNs`, `neuromorphic`

- Architecture terms (`"spiking transformer"`, `"spiking mamba"`, …) are covered by `spiking` and stay inside this block. They are never OR-ed with the HSI block alone, because `"state space" AND hyperspectral` returns non-spiking Mamba papers.
- `spike` on its own is deliberately **not** used (noise: cosmic spikes, wheat spikes, spike noise).
- Known noise from `SNN`: Siamese, self-normalizing, and subgraph-dependent networks, and **SNNS = Stuttgart Neural Network Simulator** (2009–2010 papers). All of these are E1.

**Hyperspectral block (H):**
`hyperspectral`, `"hyper-spectral"`, `"imaging spectroscopy"`, `"imaging spectrometer"`, `"spectral imaging"`

## Search IDs
`S..` = main run. `P..` = pilot. `U..` = update before submission. The number is the source number (D1 → S01, D4 → S04, …). Snowballing goes in `snowball_log.csv`.

## Pilot results (2026-10-16, no date filter)

Recall is measured against the 8 independent web-search seeds. "Likely relevant" means a title/abstract heuristic hit among the 577 deduplicated pilot papers.

| Source | Hits | Seed recall | Likely relevant | Unique likely relevant |
|---|---|---|---|---|
| D1 OpenAlex | 302 | 8/8 | 62 | 10 |
| D2 Semantic Scholar | 267 | 8/8 | 55 | 3 |
| D3 arXiv | 21 | 1/8 | 3 | 0 |
| D8 Europe PMC | 10 | 0/8 | 5 | 0 |
| D9 Crossref (4 × top 100) | — | 7/8 (P09a, P09b) | 22 | 1 |
| D10 DOAJ | 14 | 1/8 | 10 | 0 |
| D4 IEEE Xplore (web endpoint) | 80 | 3/3 IEEE-published seeds | — | — |
| D11 SpringerLink | bot challenge (P11 logged as FAILED) | | | |
| D5, D7, D12 | block non-browser access | | | |

---

## Scripted sources — `python scripts/search.py <source> <ID> "<string>" --round main --until <cut-off>`

### D1 — OpenAlex (`openalex`, title_and_abstract.search; words are stemmed, no wildcards)
```
(spiking OR "spike-based" OR "spike-driven" OR "integrate-and-fire" OR spikformer OR spikingformer OR SNN OR SNNs OR neuromorphic) AND (hyperspectral OR "hyper-spectral" OR "imaging spectroscopy" OR "imaging spectrometer" OR "spectral imaging")
```

### D2 — Semantic Scholar (`semanticscholar`, bulk search: `|` OR, `+` AND)
```
(spiking | "spike-based" | "spike-driven" | "integrate-and-fire" | spikformer | spikingformer | SNN | neuromorphic) + (hyperspectral | "hyper-spectral" | "imaging spectroscopy" | "imaging spectrometer" | "spectral imaging")
```

### D3 — arXiv (`arxiv`)
```
(all:spiking OR all:"spike-based" OR all:"spike-driven" OR all:"integrate-and-fire" OR all:spikformer OR all:neuromorphic OR all:SNN) AND (all:hyperspectral OR all:"hyper-spectral" OR all:"imaging spectroscopy" OR all:"spectral imaging")
```

### D8 — Europe PMC (`europepmc`)
```
TITLE_ABS:(spiking OR "spike-based" OR "spike-driven" OR "integrate-and-fire" OR spikformer OR spikingformer OR SNN OR neuromorphic) AND TITLE_ABS:(hyperspectral OR "hyper-spectral" OR "imaging spectroscopy" OR "imaging spectrometer" OR "spectral imaging")
```

### D9 — Crossref (`crossref --top 100`, relevance-ranked, publication types only)
- S09a `spiking neural network hyperspectral`
- S09b `spiking hyperspectral image classification`
- S09c `neuromorphic hyperspectral`
- S09d `spike-driven transformer hyperspectral`

### D10 — DOAJ (`doaj`)
```
(spiking OR "spike-based" OR "spike-driven" OR "integrate-and-fire" OR spikformer OR spikingformer OR SNN OR neuromorphic) AND (hyperspectral OR "hyper-spectral" OR "imaging spectroscopy" OR "imaging spectrometer" OR "spectral imaging")
```

### D4 — IEEE Xplore (`ieee`, the site's own web search endpoint; same command-search string as in the manual section below)

### D6 — Google Scholar (`scholar --top 300`, 8–15 s between pages, stops at the first CAPTCHA)
Same four queries as S06a–S06d in the manual section below. If a run stops early, the log notes it; finish that query in Publish or Perish and import it as `S06x-pop`.

### Crossref publisher-prefix searches (`crossref --top 100 --prefix ...`)
- S05c `spiking neural network hyperspectral` with `--prefix 10.1016` (Elsevier / ScienceDirect)
- S11c `spiking neural network hyperspectral` with `--prefix 10.1007` (Springer)
- S12c `spiking neural network hyperspectral` with `--prefix 10.1145` (ACM)

---

## Manual sources — search in a browser, export, then import

```
python scripts/import_export.py <source> <ID> <downloaded file> --query "<exact string>" --hits <count shown> --fields <field> --round main
```
Record the hit count **shown on screen** before exporting. Don't rename or edit the downloaded file before importing.

### D4 — IEEE Xplore (`ieee`) — ieeexplore.ieee.org → Advanced Search → Command Search
```
("All Metadata":spiking OR "All Metadata":"spike-based" OR "All Metadata":"spike-driven" OR "All Metadata":"integrate-and-fire" OR "All Metadata":spikformer OR "All Metadata":SNN OR "All Metadata":neuromorphic) AND ("All Metadata":hyperspectral OR "All Metadata":"hyper-spectral" OR "All Metadata":"imaging spectroscopy" OR "All Metadata":"spectral imaging")
```
Export: select all results → Export → Citations → **CSV**. `--fields all_metadata`

### D5 — ScienceDirect (`sciencedirect`) — sciencedirect.com → Advanced search → "Title, abstract or author-specified keywords"
ScienceDirect allows at most 8 Boolean connectors per field, so the search runs in two parts:
- S05a `(spiking OR "spike-based" OR "spike-driven" OR "integrate-and-fire") AND (hyperspectral OR "hyper-spectral" OR "spectral imaging")`
- S05b `(SNN OR neuromorphic OR spikformer) AND (hyperspectral OR "hyper-spectral" OR "spectral imaging")`

Export: select all → Export → **RIS**, with abstracts. `--fields title_abstract_keywords`

### D6 — Google Scholar (`scholar`) — Publish or Perish (harzing.com, free) → Google Scholar search, "All of the words" box, max results **300**
- S06a `"spiking neural network" hyperspectral`
- S06b `spiking hyperspectral classification`
- S06c `neuromorphic hyperspectral`
- S06d `spikformer OR "spike-driven" hyperspectral`

Export: File → Save as CSV. `--fields full_text --interface PoP --filters top300`

### D7 — dblp (`dblp`) — open each URL in a browser (passes the bot check), then save the page as `.json`
- S07a `https://dblp.org/search/publ/api?q=spik%20hyperspectral&format=json&h=1000`
- S07b `https://dblp.org/search/publ/api?q=neuromorphic%20hyperspectral&format=json&h=1000`
- S07c `https://dblp.org/search/publ/api?q=SNN%20hyperspectral&format=json&h=1000`

dblp matches word prefixes, so `spik` covers spiking and spike-driven. `--fields title`

### D11 — SpringerLink (`springer`) — link.springer.com search box (full text)
- S11 `"spiking neural" AND hyperspectral`

If the result count is above 1,000 (the export limit), use the advanced search "title contains" field with `spiking hyperspectral` instead, and log that. Export: "Download search results (CSV)". `--fields full_text`

### D12 — ACM Digital Library (`acm`) — dl.acm.org → Advanced search, "Search within: Abstract"
- S12 `(spiking OR neuromorphic OR "spike-driven") AND hyperspectral`

Export: select all → Export citations → **BibTeX**. `--fields abstract`
