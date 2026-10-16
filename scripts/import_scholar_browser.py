"""Import a Google Scholar run captured in the reviewer's own Chrome (Claude in Chrome).

Usage:
    python scripts/import_scholar_browser.py ~/Downloads/scholar_S06a3.json [--round main] [--note TEXT]

The JSON file holds the query, the hit count Scholar showed, and the results HTML of each
page fetched (top 300, 8-15 s apart). Records are parsed with the same parser as
scripts/search.py and logged like any other search; the whole JSON file is kept as the
raw export.
"""
import argparse
import json
import pathlib
import sys
import types

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import search  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=pathlib.Path)
    ap.add_argument("--round", default="main", choices=["pilot", "main", "update"])
    ap.add_argument("--run-by", default="R1")
    ap.add_argument("--note", default="run in R1's Chrome (Claude in Chrome), top 300, 8-15 s between pages")
    args = ap.parse_args()

    data = json.loads(args.file.read_text(encoding="utf-8"))
    search.check_new(data["search_id"], "scholar")
    rows = []
    for page in data["pages"]:
        rows.extend(search.parse_scholar(page["html"])[1])
    filters = f"top{data.get('top', 300)}"
    if len(data["pages"]) * 10 < min(data["total"], data.get("top", 300)) and data["pages"][-1]["n"]:
        filters += ";PARTIAL"
    search.save_export(data["search_id"], "scholar", data["query"], data["total"], [data], rows, filters,
                       types.SimpleNamespace(round=args.round, run_by=args.run_by, note=args.note),
                       "browser", "full_text")


if __name__ == "__main__":
    main()
