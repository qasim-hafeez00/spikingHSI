# Codebook

**Conventions (all tables)**
- `paper_id` = `SH-0001`… Assigned once, at deduplication, and permanent.
- `rec_id` = `<search_id>-<4-digit n>`, e.g. `S01-0042`. One per raw exported record.
- Multi-valued cells use `;` as separator, with no spaces around it.
- `NR` = not reported in the paper. `NA` = not applicable. Blank = not yet extracted.
- Dates are ISO `YYYY-MM-DD`.
- Accuracy metrics are recorded as percentages with the paper's precision (e.g., `98.72`).
- Reviewer codes: `R1` = Muhammad Qasim Hafeez. Add new reviewers here: `R2`, `R3`, …

---

## records.csv — one row per raw exported record
| Column | Definition |
|---|---|
| rec_id | See conventions |
| search_id | Links to search_log.csv |
| source_db | `openalex`, `semanticscholar`, `arxiv`, `ieee`, `sciencedirect`, `scholar`, `dblp`, `snowball`, `seed` |
| source_record_id | ID in the source (OpenAlex W-id, arXiv id, …) |
| title, authors, year, venue, doi, url, abstract | As exported. Authors separated by `;` |
| paper_id | Assigned at deduplication |

## deduplication_log.csv
| Column | Definition |
|---|---|
| rec_id | Record being merged |
| paper_id | Paper it was merged into |
| match_type | `doi`, `title_exact`, `title_fuzzy`, `version_link`, `manual` |
| similarity | Fuzzy score 0–1 (blank for exact matches) |
| decided_by, date, notes | |

## master_registry.csv — one row per unique paper
| Column | Definition / allowed values |
|---|---|
| paper_id, title, authors, year, venue, publisher, doi, url, abstract, keywords | Bibliographic data, from the best available record |
| venue_type | `journal`, `conference`, `preprint`, `other` |
| citation_count, citation_date | Count and the date it was read (from OpenAlex) |
| source_databases | `;`-list of source_db values that retrieved the paper |
| found_via | `database`, `backward`, `forward`, `seed`, `update` |
| search_round | `main`, `update` |
| alt_dois | `;`-list of DOIs of other versions merged into this paper (e.g. the arXiv preprint of a published article) |
| venue_flag | `ok`, `suspect` (give the reason in notes) |
| final_status | `pending`, `excluded_TA`, `excluded_FT`, `included` |
| tier | `1A`, `1B` (included papers only) |
| domain | `remote_sensing`, `agriculture`, `food`, `medical`, `industrial`, `other` |
| multimodal | `yes`, `no` |
| zotero_key | Zotero item key (PDFs live in Zotero, not git) |
| first_rec_id | rec_id of the record that first created this paper (set by script) |
| notes | |

## screening.csv — one row per paper × stage × reviewer × round
| Column | Allowed values |
|---|---|
| paper_id | |
| stage | `TA` (title/abstract), `FT` (full text) |
| round | `primary`, `rescreen` (intra-rater check), `calibration` |
| reviewer | `R1`, `R2`, … |
| decision | `include`, `exclude`, `maybe` (`maybe` is allowed at TA only and is treated as include) |
| exclusion_code | `E1`–`E9` (Protocol §4.2). Required at FT when excluding |
| date, notes | |

## extraction.csv — one row per included paper
If a paper proposes several distinct models, add one row per model with the same `paper_id` and a distinct `model_name`.

| Column | Allowed values / definition |
|---|---|
| paper_id, model_name | Model name as given by the authors |
| task | `classification`, `segmentation`, `fewshot_classification`, `cross_domain_classification`, `unmixing`, `denoising`, `anomaly_detection`, `target_detection`, `change_detection`, `band_selection`, `super_resolution`, `compressive_reconstruction`, `regression`, `other:<text>` |
| architecture_family | `;`-list: `spiking_cnn`, `spiking_resnet`, `spiking_transformer`, `spiking_ssm` (Mamba/SSM), `spiking_gnn`, `spiking_rnn` (LSTM/GRU/recurrent), `spiking_mlp`, `spiking_kan`, `hybrid_snn_ann`, `other:<text>` |
| base_model | Named base model the work builds on (feeds background set B1), e.g. `Spikformer`, `SEW-ResNet` |
| neuron_model | `IF`, `LIF`, `PLIF`, `ALIF`, `Izhikevich`, `SRM`, `multi_threshold`, `other:<text>`, `NR` |
| spike_encoding | `direct` (analog input to first spiking layer), `rate_poisson`, `rate_other`, `ttfs` (time to first spike), `latency`, `phase`, `delta`, `population`, `learned`, `other:<text>`, `NR` |
| learning_method | `surrogate_gradient`, `ann_snn_conversion`, `conversion_plus_finetune`, `stdp`, `other_local`, `other:<text>`, `NR` |
| surrogate_or_conversion_detail | Free text, e.g. "arctan surrogate", "threshold balancing" |
| timesteps | Integer, or a `;`-list if several were evaluated |
| spectral_handling | Free text: how the spectral dimension is processed (e.g., "3D conv on full cube", "spectral tokens", "spectral SSM scan") |
| spectral_handling_class | `full_cube_3d`, `spectral_branch`, `spectral_tokens`, `band_reduced_2d`, `pixel_spectrum_1d`, `other:<text>` |
| spatial_handling | Free text |
| input_patch_size | e.g. `11x11`, `NA` for pixel-only models |
| dimensionality_reduction | `PCA:<n>`, `band_selection:<n>`, `learned`, `none`, `other:<text>`, `NR` |
| datasets_used | `;`-list of names from the dataset list below |
| ann_counterpart_compared | `yes`, `no` |
| runs_or_seeds | Integer or `NR` |
| parameters | As reported, with units (e.g. `0.42M`) |
| flops_or_sops | As reported, with units |
| energy_value | As reported, with units |
| energy_method | `measured_hardware`, `estimated_ops`, `estimated_other`, `NR` |
| energy_assumptions | e.g. `45nm; E_AC=0.9pJ; E_MAC=4.6pJ` |
| hardware | Neuromorphic or other hardware used for deployment or measurement, e.g. `Loihi`, `GPU-only`, `NR` |
| latency | As reported, with units |
| code_url | URL or `NR` |
| stated_limitations | Free text, as stated by the authors |
| reviewer, reviewer_notes | |

**Dataset names (use exactly):** `IndianPines`, `PaviaU`, `PaviaC`, `Salinas`, `SalinasA`, `KSC`, `Botswana`, `Houston2013`, `Houston2018`, `WHU-Hi-LongKou`, `WHU-Hi-HanChuan`, `WHU-Hi-HongHu`, `Xuzhou`, `Trento`, `MUUFL`, `Augsburg`, `Chikusei`, `WashingtonDC`, `Urban`, `Samson`, `JasperRidge`, `Cuprite`, `QUH-*` (exact variant), `other:<name>`. Add new names here when you first meet them.

## results.csv — long format, one row per paper × dataset × method × protocol
| Column | Allowed values / definition |
|---|---|
| paper_id, dataset | Dataset name from the list above |
| method | Method name as in the paper |
| method_role | `proposed`, `ann_counterpart`, `spiking_baseline` (other ANN baselines are not extracted) |
| split_type | `fixed_per_class`, `random_ratio`, `official_disjoint` (e.g. GRSS Houston), `spatial_disjoint_custom`, `other:<text>`, `unclear` |
| split_value | e.g. `10%`, `20/class` |
| OA, AA, kappa | Percent (kappa × 100) |
| OA_std, AA_std, kappa_std | If reported |
| timesteps | For this result row |
| other_metrics | `name=value;name=value` (for 1B tasks: RMSE, AUC, PSNR, SAM, …) |
| source_in_paper | e.g. `Table 5`, `Fig. 7` (required) |
| reviewer, notes | |

## quality.csv — one row per included paper × reviewer
| Column | Allowed values |
|---|---|
| paper_id, reviewer | |
| Q1 … Q8 | `yes`, `partial`, `no`, `NA` (item text in Protocol §10.1) |
| Q2_leakage_detail | Free text: how the split relates to patch overlap |
| notes | |

## search_log.csv — one row per executed search
| Column | Definition |
|---|---|
| search_id | See search_strings.md |
| date | |
| database | `source_db` value |
| interface | `API`, `web`, `PoP` (Publish or Perish) |
| fields | e.g. `title_abstract`, `all_metadata`, `full_text` |
| query_string | Verbatim |
| filters | e.g. `to_publication_date:2026-10-31`; `none` |
| hits | Count reported by the source |
| exported | Number of records exported |
| export_file | Path under `data/raw_exports/` |
| round | `pilot`, `main`, `update` |
| run_by, notes | |

## snowball_log.csv — one row per (round × seed paper × direction)
| Column | Definition |
|---|---|
| round | 1, 2, … |
| seed_paper_id | |
| direction | `backward`, `forward` |
| tool | `openalex`, `semanticscholar`, `scholar`, `manual` |
| candidates | Number of references or citations examined |
| new_records | Number not already in records.csv |
| new_included | Filled after screening |
| date, run_by | |

## seeds.csv — pilot seed set (Protocol §7.4)
`seed_id, title, doi, year, how_known` (`own_collection`, `scholar_pass`, `supervisor`, …)

## background_set.csv
| Column | Definition |
|---|---|
| bg_id | `BG-001`… |
| title, year, venue, doi | |
| rule | `B1`, `B2`, `B3` |
| kind | `architecture`, `training_method`, `neuron_model`, `hardware`, `survey` |
| architecture_family | Same vocabulary as extraction |
| key_idea | One line |
| applied_to_hsi_by | `;`-list of paper_ids, or `none` |
| notes | |
