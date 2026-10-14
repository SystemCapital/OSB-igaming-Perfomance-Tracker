# Claude Code routine for "US iGaming & OSB National Tracker"

The live routine is **OSB iGaming National Tracker weekly refresh (cloud)** (`trig_01MiWmcJC2V5oxcyVp3RmjHd`). See or edit it at https://claude.ai/code/routines/trig_01MiWmcJC2V5oxcyVp3RmjHd. If you edit the prompt there, update the copy below to match.

**Settings**
- **Schedule:** weekly, Friday 8:46am Sydney time (`CRON_TZ=Australia/Sydney 46 8 * * 5`). NYSGC posts each week (ending Sunday) on the following Wednesday US time, and most regulators publish monthly, so a weekly run picks each month up within days.
- **Environment:** "OSB Tracker", whose network access reaches the regulator sites. An environment on the default "Trusted" level only reaches package registries and GitHub, so the run could not open any source. That is what happened on 13 Oct 2026, when an earlier routine ran in the "OS Performance Tracker" environment.
- **Each run:** starts a fresh session, attaches this repository itself with `add_repo`, pushes to `main`, and republishes the artifact https://claude.ai/artifact/2HadKEUvvZa7uE7nHBanfD when figures changed.
- **Connectors:** none needed.

**Prompt**

```text
Weekly refresh of the US iGaming & OSB National Tracker in the GitHub repository SystemCapital/OSB-igaming-Perfomance-Tracker, then republish of its Claude artifact. This is an unattended scheduled run: nobody is watching, so do not ask questions. Finish the run and report.

1. Repository. If the repository is not already checked out in your working directory, attach it with the add_repo tool (owner "SystemCapital", repo "OSB-igaming-Perfomance-Tracker", access "push") and clone it. Work from the latest main: `git fetch origin main && git checkout -B main origin/main`. Use `python3` wherever CLAUDE.md says `python`.

2. Read CLAUDE.md at the repository root in full and follow it exactly: the accuracy rules, the tracker-specific instructions ("Every run, in this order": staleness sweep, NY weekly, newly published months, vendor file) and the update procedure. It is the source of truth; the steps here add to it and do not replace it. The vendor file (`Full Dataset <Mon YY>.xlsx`) is not available to this run, so skip step 4 of "Every run" unless that file is in the repository.

3. Network. Open the primary sources listed in CLAUDE.md directly (WebFetch, or curl/python3 for Excel, PDF and API files). If the egress proxy refuses the regulator hosts (HTTP 403 on CONNECT, or connection errors on most of them), say so in the first line of the report, change no figure you cannot source, and still do the staleness sweep and the log line. Never fill a gap with an estimate, a rounded press figure presented as final, or a prior-year figure.

4. Update. Run the update procedure in CLAUDE.md in order: edit data/*.json; `python3 scripts/set_snapshot.py`; `python3 scripts/new_links.py --check`; `python3 scripts/build_standalone.py`; `python3 scripts/validate.py`, which must print VALIDATION PASSED; append the line to refresh-log.md naming the source (URL or file) of every changed state-month or week. If validation still fails after you have tried to fix the data, do not commit; stop and report the errors.

5. Commit and push to main. Commit data/, OSB_iGaming_National_Tracker.html and refresh-log.md with the message "Data refresh YYYY-MM-DD: <one-line summary>" and push straight to main with `git push origin HEAD:main`. This routine is authorised to push to main every week; do not open a pull request. If the push is rejected because main has moved, run `git pull --rebase origin main`, rebuild with build_standalone.py, validate again, commit any rebuild and push again. If git refuses the push for any other reason, push to a new branch claude/refresh-YYYY-MM-DD instead, skip step 6 and put the exact error at the top of the report.

6. Republish the artifact. Do this only when validation passed, your working tree matches origin/main after your push, and this run changed at least one figure in data/ (a run that only moved the snapshot date does not republish).
   a. Check the build is artifact-safe: OSB_iGaming_National_Tracker.html must contain `<script data-tracker-main>` and must not contain `type="text/plain" data-tracker-app`. Scripts injected at runtime are refused in the artifact sandbox and leave an empty page. If either check fails, do not publish; report "artifact not republished: build still uses the runtime loader".
   b. Read the whole file before publishing it; a pattern search or a scan never stands in for reading. It is about 1.6 MB and some lines are far too long for the Read tool, so make a wrapped copy that keeps every character: `fold -w 1000 OSB_iGaming_National_Tracker.html > <your scratchpad directory>/tracker.folded.txt && wc -l <that file>`. Split the reading across 6 subagents (Agent tool, general-purpose), started together in one message, each given one consecutive range of lines so that the 6 ranges cover line 1 to the last line with no gap. Tell each subagent: read every line of its range with the Read tool on the folded file in parts of 40 lines (offset/limit, allow_large: true), and re-read a part that is refused as too large in halves; then report the first and last line it read, whether it read every line of the range, and anything that must not be published: credentials, keys or tokens, personal contact details of private individuals, or harmful content (gaming revenue figures, state and operator names, the Chart.js library code and the page's own code are expected). Publish only when every subagent has reported its whole range read and nothing of concern. Otherwise do not publish; report which lines and what.
   c. Use the Artifact tool (load it with ToolSearch if it is deferred). First read the existing artifact with action "read" and url "https://claude.ai/artifact/2HadKEUvvZa7uE7nHBanfD". Then publish to that same url: action "publish", url as above, file_path the absolute path of the repository's OSB_iGaming_National_Tracker.html. It replaces the whole page, so publish it as is. Do not pass files, capabilities, icon or force, and never publish without the url, which would create a separate artifact. If the publish is refused or asks for approval, do not retry; report the exact message.

7. Report. End with a short summary:
   - the snapshot date set;
   - the staleness sweep: each state more than one month behind, and why it lags;
   - the week NY weekly is current to;
   - each verified change (state, vertical, month or week, figures) with its source, or "No verified changes";
   - unconfirmed or interim items, and sources that were blocked or could not be checked;
   - the commit SHA pushed and its branch, or why nothing was pushed;
   - the artifact version published and the line ranges the subagents read, or why it was not republished.
```

**Retired routines.** Before this repository existed, the tracker was a single HTML file in OneDrive, updated by Cowork routines: CT, NJ, MI and PA monthly; DE/RI/WV (two routines); OSB small states monthly; and NY weekly. They were disabled on 14 Oct 2026 because they edit the OneDrive copy, not this repository. This routine covers all of their work through CLAUDE.md.
