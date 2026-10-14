# Refresh log

One line per data update: what was verified and changed, or that nothing was.

- **2026-10-13** (conversion): Moved from the single file `OSB_iGaming_National_Tracker.html` into this repository; data split into `data/*.json`, content unchanged (snapshot October 13, 2026).
- **2026-10-13** (conversion): imported from the single-file tracker. Earlier refresh history is in `refresh-log.md` in the parent OneDrive folder (shared with the Regulatory Dashboard).
- **2026-10-13** (Claude Code): page layout only - the view tabs, filters and coverage table now fit a phone-width screen (CSS inside the existing `max-width: 900px` rule; desktop unchanged). Added `.gitignore`. No data changes.
- **2026-10-14** (Claude Code): fixed the Claude artifact showing an empty dashboard. `scripts/build_standalone.py` now runs the page code as ordinary inline scripts in the single-file build instead of injecting it at runtime (the likely cause: a sandbox with a nonce-based Content-Security-Policy refuses injected scripts, which gives exactly this empty page when reproduced locally). Added an on-page error log (`data-tracker-diagnostics` in `index.html`). No data changes.
