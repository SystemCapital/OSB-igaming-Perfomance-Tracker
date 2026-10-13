# Claude Code routine for "US iGaming & OSB National Tracker"

Create it at **claude.ai/code/routines** (or `/schedule` in the Claude Code CLI).

**Settings**
- **Repository:** this repo.
- **Schedule:** weekly, Friday 9:00am Sydney time (NY posts the prior week Thu/Fri; regulators publish monthly, so a weekly run picks each month up within days).
- **Environment / network access:** **Full** (or Custom, listing the sites this tracker's sources live on). The default "Trusted" level only reaches package registries and GitHub, so Claude could not open sources or check links.
- **Branch:** routines push to a `claude/...` branch by default. The prompt below pushes to `main`; use the alternative line to review each update as a pull request instead.

**Prompt**

```text
Update the "US iGaming & OSB National Tracker" tracker in this repository.

Follow CLAUDE.md exactly, especially the accuracy rules: only change data that sources found in this session support; never invent dates, figures, names, identifiers or URLs; when in doubt leave the value unchanged and list the item as unconfirmed.

Research what changed since the snapshot date in data/meta.json, then run the full update procedure from CLAUDE.md: edit data/*.json, set the snapshot date, check new links, rebuild OSB_iGaming_National_Tracker.html, run scripts/validate.py until it passes, append a line to refresh-log.md.

Commit with the message "Data refresh YYYY-MM-DD: <summary>" and push directly to the main branch.

End with a short summary: verified changes (with sources), unconfirmed items, links you could not verify.
```

**Alternative final line (review first):**

```text
Push to a new branch named claude/refresh-YYYY-MM-DD and open a pull request into main describing the changes.
```
