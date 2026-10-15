# Spiking Neural Networks for Hyperspectral Imaging: A Systematic Review — Protocol

| | |
|---|---|
| Version | 1.0 (FROZEN) |
| Date | 2026-10-16 |
| Status | Frozen 2026-10-16 after the search pilot (git tag `protocol-v1.0`). **Search cut-off date: 2026-10-16.** OSF registration pending. Frozen at R1's decision without prior supervisor review; supervisor comments will be handled as amendments. |
| Reviewers | R1: Muhammad Qasim Hafeez (all stages). Further reviewers to be added; see Section 8.4. |
| Reporting | PRISMA 2020; PRISMA-S for search reporting |
| Method guidance | Kitchenham & Charters (2007) SLR guidelines; Wohlin (2014) snowballing guidelines |

Changes after freezing are recorded only in `amendments.md`, with date, reason, and affected sections.

---

## 1. Rationale

Spiking neural networks (SNNs) process information as discrete spike events and promise lower energy use on neuromorphic hardware. Hyperspectral images (HSI) are high-dimensional (hundreds of contiguous bands) and are increasingly processed on power-constrained platforms such as satellites, UAVs, and field devices. These two facts motivate applying spiking models to HSI.

A scoping search (Section 7.3) showed the intersection is small but growing fast: about 30 relevant records through October 2026, with more than half published in 2025–2026. The applied architectures now include spiking CNNs, transformers, state-space (Mamba) models, graph networks, and KANs. No systematic review of this intersection was found. On 2026-10-16, OpenAlex (spiking/neuromorphic × hyperspectral/remote sensing × review/survey) and a web search returned no review dedicated to SNNs for hyperspectral or remote-sensing data. The closest works are general SNN surveys (e.g., Nunes et al., IEEE Access 2022), a 2025 review of SNNs in imaging in general ("Spiking Neural Networks in Imaging: A Review and Case Study"), and deep-learning HSI surveys that do not cover spiking models. This review is distinct because it is systematic, specific to HSI, and includes a comparative and quality analysis.

## 2. Research questions

| ID | Question | Main data sources |
|---|---|---|
| RQ1 | Which spiking architectures, neuron models, spike-encoding schemes, and training methods have been applied to which HSI tasks? | extraction.csv |
| RQ2 | How do spiking HSI models handle the spectral dimension (encoding, dimensionality reduction, spectral-spatial fusion)? | extraction.csv |
| RQ3 | How do spiking models perform relative to non-spiking counterparts and other baselines, and under which evaluation protocols? | results.csv, quality.csv |
| RQ4 | How are efficiency and energy claims made (measured vs. estimated, under which assumptions), and are they substantiated? | extraction.csv, quality.csv |
| RQ5 | What evaluation, reproducibility, and coverage gaps exist, including architecture families and HSI tasks not yet combined? | quality.csv, gap matrix, background_set.csv |

## 3. Review type

This is a systematic review with a structured narrative synthesis, a taxonomy, tabulated comparative results, and quality appraisal. No meta-analysis is planned, because evaluation protocols are heterogeneous (Section 10).

## 4. Eligibility criteria

### 4.1 Inclusion (all must hold)

- **I1 — Spiking model.** The paper proposes, adapts, or evaluates a model whose evaluated pipeline contains spiking neurons, meaning units that emit discrete spike or binary events over time steps (e.g., IF, LIF, PLIF, Izhikevich, SRM). Spiking models obtained by ANN-to-SNN conversion count. Hybrid SNN–ANN models count if at least one spiking component is part of the evaluated model.
- **I2 — Hyperspectral imaging data.** The model is applied to data acquired by an imaging spectrometer and described by the authors as hyperspectral. Multimodal inputs (e.g., HSI + LiDAR, HSI + SAR) qualify if HSI is one of the inputs. Any application domain qualifies (remote sensing, agriculture/food, medical, industrial, etc.). Pixel spectra or averaged spectra extracted from HSI cubes qualify.
- **I3 — Empirical evaluation.** The paper reports experimental results of the spiking model on HSI data (simulation or hardware).
- **I4 — Publication type.** Peer-reviewed journal article, peer-reviewed conference paper, or preprint (arXiv or similar).
- **I5 — Language.** English.
- **I6 — Date.** No lower bound. Upper bound is the search cut-off date recorded in `search_log.csv`, plus the pre-submission update search (Section 7.5).

### 4.2 Exclusion codes

Record one primary code per excluded paper in `screening.csv`.

| Code | Reason | Notes |
|---|---|---|
| E1 | No spiking model | Includes "spike" homonyms: cosmic-ray spikes, wheat/cereal spikes, sample spiking in chemometrics, spike noise |
| E2 | Not hyperspectral imaging data | Multispectral, RGB, SAR, or LiDAR only; non-imaging 1-D spectra (point NIR/Raman/FTIR spectrometers) |
| E3 | Neuromorphic hardware, device, or sensor without a spiking model evaluated on HSI | Candidate for the background set (Section 6) |
| E4 | No empirical evaluation on HSI | Position papers, conceptual frameworks |
| E5 | Secondary study (review, survey) | Not included, but used as a snowballing source |
| E6 | Ineligible publication type | Thesis, patent, abstract-only, editorial, book front matter |
| E7 | Non-English | |
| E8 | Full text unavailable after a library request | Log the request date |
| E9 | Duplicate or superseded version | Normally caught at deduplication; the preprint is merged into its published version (DOI kept in `alt_dois`) |

### 4.3 Venue quality

Papers in venues suspected to be predatory are **not** excluded on that basis. They are flagged (`venue_flag = suspect`) with a written reason, and the synthesis is checked with and without them (Section 10.4).

### 4.4 Tiers (assigned at full-text stage)

| Tier | Scope |
|---|---|
| 1A | HSI classification, including pixel-wise segmentation, land-cover mapping, few-shot/cross-domain classification, and multimodal classification |
| 1B | Other HSI tasks: unmixing, denoising/restoration, anomaly or target detection, change detection, band selection, super-resolution, compressive reconstruction, regression/property estimation |

Domain (remote sensing, agriculture, food, medical, other) and `multimodal` (yes/no) are tagged separately.

## 5. Search scope decision (scoping-informed)

An earlier draft had a conditional Phase 2 covering spiking models × broader remote sensing (multispectral, SAR, scene classification). It was **dropped before freezing**, on the basis of the scoping search (Section 7.3): the HSI intersection alone gave about 30 relevant records from a single database at title level, which is sufficient. The scope is fixed and has no conditional extension.

## 6. Background set (non-systematic)

The background set is a separate, explicitly non-systematic list of spiking architectures and methods. It supports the taxonomy (RQ1) and the gap analysis (RQ5). It is reported as such and is not counted in PRISMA. Selection rules:

- **B1.** Any spiking architecture or training method that an included paper names as its base model.
- **B2.** Landmark spiking architecture families named in at least two of the reference SNN surveys listed in `background_set.csv` (surveys to be chosen and listed before the gap analysis).
- **B3.** Neuromorphic hardware platforms used or targeted by included papers, plus E3-coded papers.

## 7. Information sources and search

### 7.1 Sources

Only free sources are used. No Scopus or Web of Science subscription is available, so OpenAlex is the primary bibliographic database.

| ID | Source | Interface | Role |
|---|---|---|---|
| D1 | OpenAlex | API (`scripts/search.py`) | Primary database |
| D2 | Semantic Scholar | API (bulk search) | Database |
| D3 | arXiv | API | Preprints |
| D4 | IEEE Xplore | Web command search, CSV export | Publisher database (TGRS, GRSL, JSTARS, TNNLS, IGARSS) |
| D5 | ScienceDirect | Web advanced search, RIS export | Publisher database (Elsevier) |
| D6 | Google Scholar | Publish or Perish (free), CSV export | Full-text search; supplementary |
| D7 | dblp | Search API opened in a browser, JSON | Computer-science bibliography |
| D8 | Europe PMC | API | Medical, agricultural and food HSI |
| D9 | Crossref | API, top 100 by relevance per query (no Boolean search) | Supplementary metadata search |
| D10 | DOAJ | API | Open-access journals (MDPI, Hindawi, etc.) |
| D11 | SpringerLink | Web search, CSV export | Publisher database (Springer Nature) |
| D12 | ACM Digital Library | Web advanced search, BibTeX export | Computing venues |
| — | Citation chasing | OpenAlex / Semantic Scholar references and citations | Backward and forward snowballing |

Access route per source (fixed at the freeze):

- **D1–D3, D8–D10:** official APIs (`scripts/search.py`).
- **D4 IEEE Xplore, D6 Google Scholar:** the sites' own web search endpoints, read the way a browser would (`scripts/search.py ieee|scholar`). Google Scholar is paged slowly and the run stops at the first CAPTCHA. No attempt is made to get past a CAPTCHA. If it stops early, the search is finished in Publish or Perish and imported.
- **D5 ScienceDirect, D7 dblp, D11 SpringerLink, D12 ACM DL:** these sites block non-browser access with a sign-in redirect or a bot challenge. They are searched by hand in a browser and the exports imported (`scripts/import_export.py`), or through a free publisher API key if one is obtained.
- **Crossref publisher-prefix searches:** run for every one of D5, D11 and D12, regardless of whether the manual search is done. Crossref is searched restricted to each publisher's DOI prefix (10.1016 Elsevier → S05c, 10.1007 Springer → S11c, 10.1145 ACM → S12c), top 100 by relevance.
- **dblp:** its records are already indexed by OpenAlex and Semantic Scholar. A manual dblp search that is not done is reported as a limitation.

**Limitation to report:** Scopus and WoS were not searched. This is mitigated by OpenAlex's broad coverage, by the publisher databases, by full-text Google Scholar searching, and by exhaustive snowballing. *(Add a citation for an OpenAlex coverage comparison study.)*

### 7.2 Search structure

**Spiking block** AND **hyperspectral block**, searched in title, abstract, and keywords (Google Scholar: full text). No date lower bound. Exact per-source strings are in `search_strings.md`, and every executed string is logged verbatim in `search_log.csv`.

### 7.3 Scoping search (already performed, reported for transparency)

Done on 2026-10-16 in OpenAlex (title_and_abstract search). Its only purposes were to estimate volume and to decide scope (Section 5). No screening decisions were made from it.

| Query | Raw hits | Title-level SNN hits |
|---|---|---|
| spiking terms AND hyperspectral | 181 | 37 (~30 judged relevant) |
| neuromorphic AND hyperspectral | 36 | — |
| spiking AND "spectral imaging"/"imaging spectroscopy" NOT hyperspectral | 55 | — |
| spiking/neuromorphic AND remote-sensing terms NOT hyperspectral | 2,542 | — (Phase 2 dropped) |
| SNN phrases AND 1-D spectroscopy terms NOT hyperspectral | 1,244 | ~10 in top 200 (non-imaging spectra excluded, E2) |

Year profile of the relevant hits: first appearance in 2018, then 2022 (4), 2024 (5), 2025 (8), 2026 to date (17).

Main noise sources found: wheat "spikes", cosmic-ray spikes in Raman HSI, sample "spiking" in chemometrics, and memristor/synaptic-device papers.

### 7.4 Pilot (before freezing)

1. Assemble a **seed set** (`seeds.csv`) from sources independent of OpenAlex: papers already known to the reviewer, plus a Google Scholar pass.
2. Run every draft string. Check that the combined strategy retrieves 100% of the seeds (`scripts/check_seed_recall.py`), and report recall per source.
3. Revise strings until recall is complete or every miss is explained. Record the revisions.
4. Search explicitly for existing reviews or surveys of SNN × HSI (or SNN × remote sensing). If any exist, cite them and state how this review differs.
5. Freeze the protocol (tag `protocol-v1.0`) and register it on OSF.

### 7.5 Supplementary searching

- **Snowballing:** backward (reference lists) and forward (citing papers) from every included paper and from E5 surveys. Repeat in rounds until a round adds no new included paper. Each round is logged in `snowball_log.csv`.
- **Update search:** before manuscript submission, re-run all database searches restricted to dates after the cut-off. New records go through the same pipeline as `search_round = update`.

## 8. Selection process

### 8.1 Records and deduplication

Each raw exported record gets a `rec_id` in `records.csv`. Raw export files in `data/raw_exports/` are never edited. Deduplication proceeds in order:

1. Exact DOI match.
2. Normalized title + year match.
3. Fuzzy title match (similarity ≥ 0.90), confirmed manually.
4. Preprint and published versions of the same work are merged into one `paper_id` (`match_type = version_link`). The published version supplies the metadata, and the preprint DOI is kept in `alt_dois`. Matches the script cannot make (e.g. a changed title) are forced in `data/dedup_overrides.csv`.

Each unique paper gets a permanent `paper_id` (`SH-0001`, …), used in all tables. Every merge is logged in `deduplication_log.csv`.

### 8.2 Screening stages

1. **Title/abstract:** liberal. If in doubt, include.
2. **Full text:** apply I1–I6 strictly and record one exclusion code per excluded paper.

### 8.3 Single-reviewer safeguards (current phase)

R1 screens everything. To measure consistency:

- **Intra-rater check:** a random 20% sample of title/abstract decisions (fixed random seed, recorded) is re-screened after a washout of at least 14 days, without access to the earlier decisions. Report Cohen's κ. If κ < 0.8, re-screen all records excluded at title/abstract.
- All full-text exclusions are recorded with a reason code. A supervisor spot-check of a sample of exclusions is recommended.

### 8.4 When additional reviewers join

- **Calibration:** new reviewers screen 50 records already decided by R1, without seeing R1's decisions. Compute κ against R1. Discuss disagreements and refine the codebook before allocating independent work. Target κ ≥ 0.6.
- **Ongoing:** at least a 20% overlap between reviewers. Conflicts are resolved by discussion, then by an adjudicator (supervisor).
- **Extraction verification:** a second reviewer independently checks at least 20% of extraction rows and **all** `results.csv` rows against `source_in_paper`.

## 9. Data extraction

Extraction uses `extraction.csv`, `results.csv`, and `quality.csv`. All fields and allowed values are defined in `codebook.md`. Extraction rules:

- Record values as reported. Do not infer. Use `NR` (not reported) and `NA` (not applicable). A blank cell means not yet extracted.
- `results.csv` records only: the proposed method(s), the paper's non-spiking counterpart (if any), and all spiking baselines. Other ANN baselines are not extracted.
- Every number in `results.csv` cites its table or figure in `source_in_paper`.
- Accuracy metrics are recorded as percentages.

## 10. Quality appraisal and synthesis

### 10.1 Quality checklist

Each item is scored yes / partial / no / NA in `quality.csv`. No total score is computed: items are reported per paper and as frequencies.

| ID | Item |
|---|---|
| Q1 | Train/test split protocol is fully described (sampling scheme, ratio or per-class count, validation set). |
| Q2 | Spatial leakage is addressed: spatially disjoint splits are used, or overlap of patches between train and test is acknowledged or controlled. |
| Q3 | Results are averaged over repeated runs or seeds, with variance reported. |
| Q4 | The spiking model is compared with its own non-spiking counterpart (same architecture). |
| Q5 | Baselines are recent and evaluated under the same protocol (rerun, not copied across protocols). |
| Q6 | The energy or efficiency claim states its method: hardware measurement, or operation-count estimate with stated per-operation costs and process node. |
| Q7 | Code is publicly available. |
| Q8 | Spiking hyperparameters are reported (time steps, thresholds, neuron model, surrogate function or conversion method). |

### 10.2 Synthesis

- **RQ1 and RQ2:** a taxonomy (architecture family × neuron/encoding/learning × spectral handling) with summary tables and year trends.
- **RQ3:** results are compared only **within** groups that share dataset × split type × split value. Papers are never ranked across differing protocols. Spiking-vs-ANN gaps are reported where Q4 holds.
- **RQ4:** energy claims are tabulated by method (measured vs. estimated) and by stated assumptions.
- **RQ5:** a gap matrix of architecture family × HSI task, using included papers plus the background set, combined with quality-item frequencies.

### 10.3 Heterogeneity

Datasets, splits, patch sizes, and time steps vary too widely for meta-analysis. Synthesis is structured narrative with tabulation.

### 10.4 Sensitivity checks

Repeat the key summaries (a) excluding `venue_flag = suspect` papers and (b) excluding preprints with no published version.

## 11. Data management

- Version-controlled repository (git). Pushed to a free private GitHub repository once collaborators join.
- References and PDFs are kept in Zotero (free tier). PDFs are **not** committed to git (copyright).
- The flat master sheet is generated by a script from the linked tables and never edited by hand.
- Data and code are released openly at publication.

## 12. Amendments

See `amendments.md`.
