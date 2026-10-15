#!/usr/bin/env bash
# Official (main-round) database searches, protocol-v1.0. Strings: protocol/search_strings.md.
# Google Scholar runs separately (slow, CAPTCHA-sensitive): see the end of this file.
set -euo pipefail
cd "$(dirname "$0")/.."
CUT=2026-10-16
R="--round main --until $CUT"

python scripts/search.py openalex S01 '(spiking OR "spike-based" OR "spike-driven" OR "integrate-and-fire" OR spikformer OR spikingformer OR SNN OR SNNs OR neuromorphic) AND (hyperspectral OR "hyper-spectral" OR "imaging spectroscopy" OR "imaging spectrometer" OR "spectral imaging")' $R
python scripts/search.py semanticscholar S02 '(spiking | "spike-based" | "spike-driven" | "integrate-and-fire" | spikformer | spikingformer | SNN | neuromorphic) + (hyperspectral | "hyper-spectral" | "imaging spectroscopy" | "imaging spectrometer" | "spectral imaging")' $R
python scripts/search.py arxiv S03 '(all:spiking OR all:"spike-based" OR all:"spike-driven" OR all:"integrate-and-fire" OR all:spikformer OR all:neuromorphic OR all:SNN) AND (all:hyperspectral OR all:"hyper-spectral" OR all:"imaging spectroscopy" OR all:"spectral imaging")' $R
python scripts/search.py ieee S04 '("All Metadata":spiking OR "All Metadata":"spike-based" OR "All Metadata":"spike-driven" OR "All Metadata":"integrate-and-fire" OR "All Metadata":spikformer OR "All Metadata":SNN OR "All Metadata":neuromorphic) AND ("All Metadata":hyperspectral OR "All Metadata":"hyper-spectral" OR "All Metadata":"imaging spectroscopy" OR "All Metadata":"spectral imaging")' $R
python scripts/search.py europepmc S08 'TITLE_ABS:(spiking OR "spike-based" OR "spike-driven" OR "integrate-and-fire" OR spikformer OR spikingformer OR SNN OR neuromorphic) AND TITLE_ABS:(hyperspectral OR "hyper-spectral" OR "imaging spectroscopy" OR "imaging spectrometer" OR "spectral imaging")' $R
python scripts/search.py crossref S09a 'spiking neural network hyperspectral' --top 100 $R
python scripts/search.py crossref S09b 'spiking hyperspectral image classification' --top 100 $R
python scripts/search.py crossref S09c 'neuromorphic hyperspectral' --top 100 $R
python scripts/search.py crossref S09d 'spike-driven transformer hyperspectral' --top 100 $R
python scripts/search.py doaj S10 '(spiking OR "spike-based" OR "spike-driven" OR "integrate-and-fire" OR spikformer OR spikingformer OR SNN OR neuromorphic) AND (hyperspectral OR "hyper-spectral" OR "imaging spectroscopy" OR "imaging spectrometer" OR "spectral imaging")' --round main --note "DOAJ API has no date filter; post-cut-off records excluded at screening"
python scripts/search.py crossref S05c 'spiking neural network hyperspectral' --top 100 --prefix 10.1016 $R
python scripts/search.py crossref S11c 'spiking neural network hyperspectral' --top 100 --prefix 10.1007 $R
python scripts/search.py crossref S12c 'spiking neural network hyperspectral' --top 100 --prefix 10.1145 $R

# Google Scholar (run separately; 8-15 s between pages, stops at first CAPTCHA):
# python scripts/search.py scholar S06a '"spiking neural network" hyperspectral' --top 300 $R
# python scripts/search.py scholar S06b 'spiking hyperspectral classification' --top 300 $R
# python scripts/search.py scholar S06c 'neuromorphic hyperspectral' --top 300 $R
# python scripts/search.py scholar S06d 'spikformer OR "spike-driven" hyperspectral' --top 300 $R
