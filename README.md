# US iGaming & OSB National Tracker

A tracker dashboard kept in GitHub and updated by Claude Code.

## View it

Open **`OSB_iGaming_National_Tracker.html`**: one self-contained file with the data and libraries embedded. It works offline and opens by double-click. On GitHub: click the file > **Download raw file**.

## Layout

```
OSB_iGaming_National_Tracker.html     ready-to-open dashboard (generated - don't edit by hand)
index.html         dashboard source page; loads data/*.json
data/              all tracker data (one JSON file per dataset) + meta.json + schema.json
vendor/            third-party libraries the page uses (licences included)
scripts/           validate.py, build_standalone.py, set_snapshot.py, new_links.py, render_check.js
CLAUDE.md          instructions Claude Code follows for every update
ROUTINE_PROMPT.md  settings + prompt for a scheduled Claude Code routine
refresh-log.md     one line per update
```

## Datasets

| File | Shape | Rows/keys | Fields with roles |
|---|---|---|---|
| `data/RAW.json` | keyed object | 2 | - |
| `data/DET_IG.json` | keyed object | 3 | - |
| `data/DET_OSB.json` | keyed object | 3 | - |
| `data/DET_COVERAGE_IG.json` | rows of 4 fields | 7 | - |
| `data/DET_COVERAGE_OSB.json` | rows of 4 fields | 35 | 2: enum |
| `data/DETAILED_NYW.json` | keyed object | 4 | - |

## Updating

Ask Claude Code ("add X", "refresh the data") or set up the routine in `ROUTINE_PROMPT.md`. Claude reads `CLAUDE.md`, edits `data/`, rebuilds `OSB_iGaming_National_Tracker.html`, validates and commits.

By hand: edit `data/*.json`, then run

```bash
python scripts/build_standalone.py
python scripts/validate.py          # must pass before committing
```

Preview `index.html` with `python -m http.server 8000` and open http://localhost:8000. Double-clicking `index.html` won't load the data; browsers block local data files.

Converted on 2026-10-13 from `OSB_iGaming_National_Tracker.html` (snapshot October 13, 2026).
