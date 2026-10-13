# CLAUDE.md - maintaining "US iGaming & OSB National Tracker"

This repository holds a tracker dashboard. Claude Code (often a scheduled routine) keeps its data current. Read this whole file before changing anything.

## Repository map

| Path | What it is | Edit? |
|---|---|---|
| `data/*.json` | ALL tracker data, one file per dataset (table below) | Yes - updates change these |
| `data/meta.json` | Title, snapshot date shown on the page, build file name | Date only via `scripts/set_snapshot.py` |
| `data/schema.json` | Validation rules inferred at conversion | Only to add a new dataset or field rule |
| `index.html` | Dashboard page. Its code runs from `<script type="text/plain" data-tracker-app>` blocks after a small loader fetches `data/*.json` | Only for requested design changes |
| `OSB_iGaming_National_Tracker.html` | Ready-to-open single-file build (data + libraries embedded) | Never by hand - run `scripts/build_standalone.py` |
| `vendor/` | Third-party libraries used by the page (with licences) | No |
| `scripts/validate.py` | Checks data shape, sources, page scripts, build freshness, render | No |
| `scripts/build_standalone.py` | Regenerates `OSB_iGaming_National_Tracker.html` | No |
| `scripts/set_snapshot.py` | Sets the snapshot date | No |
| `scripts/new_links.py` | Lists / checks source URLs added since the last commit | No |
| `scripts/render_check.js` | Simulated-browser smoke test used by validate.py | No |
| `refresh-log.md` | Audit trail - one line per update | Append only |

Scripts need Python 3.9+ (standard library only). Node.js enables the page-script and render checks.

## Datasets

| File | Shape | Rows/keys | Fields with roles |
|---|---|---|---|
| `data/RAW.json` | keyed object | 2 | - |
| `data/DET_IG.json` | keyed object | 3 | - |
| `data/DET_OSB.json` | keyed object | 3 | - |
| `data/DET_COVERAGE_IG.json` | rows of 4 fields | 7 | - |
| `data/DET_COVERAGE_OSB.json` | rows of 4 fields | 35 | 2: enum |
| `data/DETAILED_NYW.json` | keyed object | 4 | - |

Roles: `sources` = list of `["Label", "https://url"]` pairs (minimum count enforced); `link` = one `["Label", "https://url"]`; `isodate` = `YYYY-MM` or `YYYY-MM-DD`; `enum` = a short set of status values (a new value only warns). Keep every row in exactly the existing shape: same number of fields, same order, same types. Look at a few existing rows before adding one. Write JSON as UTF-8 with 1-space indent (`json.dumps(obj, ensure_ascii=False, indent=1)`); editing through a small Python script is safer than hand-editing long lines.

## Accuracy rules (official-statistics tracker)

- Every figure comes from a **state regulator / lottery publication** (monthly report, tax return, Excel, open-data API) or from the user's vendor brands file (`Full Dataset <Mon YY>.xlsx`). Copy figures **exactly, to the dollar**. Never estimate, interpolate, derive a handle from a hold %, or round.
- Secondary sources (rg.org state tables, trade press) are allowed only when the regulator file is unreachable AND the figure matches the tracker's definition for that state (check against a month already stored from the primary source). Press-rounded values are **interim**: list them in the log so they get trued up.
- **Verify the YEAR** on every press figure; news sites re-surface prior-year months (e.g. a "Virginia Aug $416.7M" article was 2025). If a figure can't be confirmed, leave the cell `null` and log it as unconfirmed.
- **Staleness is acceptable; fabrication is not.**
- These datasets carry no `sources` field; record the source (URL or file name) for every changed state-month in `refresh-log.md`.

## Tracker-specific instructions

### What it covers
US online sports betting (OSB, ~35 states) and iGaming (CT, DE, MI, NJ, PA, RI, WV): monthly state aggregates, operator/brand detail and a New York weekly view.

### Datasets
- `RAW.json` = `{osb:{State:[row...]}, igaming:{State:[row...]}}`, rows `{d:"YYYY-MM", h:handle, r:revenue (GGR), p:promos, t:tax, n:net revenue}` in whole dollars, sorted by `d`; `null` = not reported. Replace a month by removing the old row for that `d` and appending the new row, then re-sort. Never leave zero-filled placeholder rows.
  - Conventions (match the vendor file): all channels (online + retail); `t` = federal excise (0.25% of handle, OSB only) + state + local tax; OSB `n` = r − p only when p > 0, else null; iGaming `n` = r − p and `h` = null when the state doesn't report handle.
  - **Pennsylvania iGaming:** r = PGCB casino iGaming GGR, **iLottery excluded**, p = 0, n = r. The vendor file stores PA iLottery in its "promos" column, so after every brands-file load re-apply `r := r − p; p := 0; n := r` to **every** PA iGaming row.
- `DET_IG.json` / `DET_OSB.json` = `{months:[...], states:{State:{Operator:{"YYYY-MM":{h,r,p,t}}}}, meta}`. Operator sums must equal the RAW month (check this after every edit). Add a new month to `months`.
- `DETAILED_NYW.json` = `{weeks:["YYYY-MM-DD" Sunday week-ending...], ops:{Operator:{date:{h,r}}}}`: NY mobile sports wagering by operator.
- `DET_COVERAGE_*.json` = coverage notes per state.

### Every run, in this order
1. **Staleness sweep (Rule 0):** list each state's latest month in RAW.osb and RAW.igaming. Any state more than one month behind the newest month is a defect: re-check its source this run and say why it lags.
2. **NY weekly:** add every week posted after the last week in `DETAILED_NYW`. NYSGC posts a week on the Thursday or Friday after it ends. Say in the summary which week it's current to.
3. Pull newly published months from the sources below. Reconcile operator sums to statewide totals.
4. If a new `Full Dataset <Mon YY>.xlsx` exists (it sits outside this repo; the user supplies it), overwrite every state-month it covers in RAW and rebuild DET_OSB from it. Keep regulator months beyond its coverage. Then run the post-load checks: PA iLottery fix; **dropout check** (any licensee/brand over $3M the prior month that goes to 0 while the state still reports = vendor gap, so don't load it; e.g. WV Mardi Gras online, Jun to Aug 2026); scan for negative `p` or federal-only `t` (e.g. CO 2026-06).

### Sources (verified)
- **NY OSB:** gaming.ny.gov weekly + monthly Excel per operator (`/fanduel-weekly-report-excel`, `/draftkings-sport-book-…`, `/fanatics-…`, `/betmgm-…`, `/caesars-sport-book-…`, `/rush-street-interactive-…` = BetRivers, `/wynn-interactive-…` = ESPN Bet, `/ballybet-…`; same with `-monthly-report-excel`) and `/statewide-sports-wagering-monthly-report-excel`. Sheets by fiscal year ("FY 26-27", Apr to Mar). "Week-Ending" column is an Excel serial date. Use Handle and GGR.
- **CT:** Socrata API data.ct.gov `imqd-at3c` (iGaming), `xf6g-659c` (OSB). r = wagers − patron_winnings; MPI + MPTN = DraftKings, Mohegan Digital + Tribe = FanDuel, CT Lottery = PlaySugarHouse.
- **NJ:** DGE `nj.gov/oag/ge/docs/Financials/IGRTaxReturns/<YYYY>/<Month><YYYY>.pdf` (iGaming; per-skin "SKIN DETAIL" pages; line 3 win, line 11 tax, line 12 promos). OSB revenue is in `SWRTaxReturns/...` (lines 3 + 16); handle comes from the DGE press release. **Always confirm the "FOR THE MONTH OF" header**: file naming has shifted between publication month and data month.
- **PA:** PGCB revenue page; FY files (`FY26-27 Monthly Interactive Gaming Report Summary.xlsx`, `…Sports Wagering…`). Files move to new dated folders, so **always re-scrape the link** (FY filter `?field_gaming_revenue_fiscal_year_target_id=292`). Operator = ALL-CAPS row (allow `!`, e.g. LIVE! PHILADELPHIA); sum "Wagers Received" and "Gross Revenue" + "Revenue (Rake…)". Sports: the GRAND TOTAL > Total Sports Wagering block.
- **MI:** MGCB `Internet-Gaming---<YEAR>.xlsx` (stride 3: Gross, AGR, state tax; p = Gross − AGR) and `Internet-Sports-Betting---<YEAR>.xlsx` (stride 4: handle, gross, AGR, tax). Name map: theScore Bet = Hollywood, NeoGames = Firekeepers, Strive = Eagle, GAN = Four Winds, Caesars/WSOP = Caesars, Bet365 = bet365, BetPARX = betParx.
- **DE:** delottery.com FY pages (iGaming: `/More/iGaming/Revenue-Distribution/Monthly-Proceeds-And-Distribution-Financial-Year/<FY>`; OSB: `/Sports-Lottery/Sportsbooks/...`). iGaming h = table + video bets; r = (bets − win) for tables and video + poker; p = promo deductions; n = Total NGR. Single operator, BetRivers.
- **RI:** rilot.com financials modal PDFs `SportsbookSummaryFY<YYYY>.pdf`, `iGamingWebsiteDataFY<YYYY>.pdf`. About a 3-week lag.
- **OH:** casinocontrol.ohio.gov revenue page, `2026_Sports_Gaming_Revenue_ReportMM.xlsx` (the link's version number changes monthly). Row "Total Online and Retail": h, r, p (promos are NOT deductible); t = 0.25%·h + 20%·taxable.
- **VA:** Virginia Lottery letters to the Governor, rga.lis.virginia.gov (`RDnnn/PDF`). h = total wagers; r = wagers − winnings (not AGR); t = that month's 15% tax + 0.25%·h.
- **NC:** ncgaming.gov `NCSLC-Sports-Betting-Revenue-Report-<Month>-<YYYY>.pdf` (h = Total Wagering Revenue, r = Gross Wagering Revenue, t = estimated tax).
- **NV:** NGCB `monthly-revenue-report---<month>-<yyyy>.pdf`: Sports Pool win only (thousands); handle is not in the report.
- **TN** tn.gov/swac CSVs; **KS** kslottery.gov PDFs; **IA** IRGC; **CO** Division of Gaming monthly summary PDFs (free-bet deduction ended 1 Jul 2026); **ME/VT/WY/SD/NE/MS/NH/DC/MT/OR** = their lottery/commission monthly reports.
- **rg.org/statistics/us/<state>** tables copy regulator figures. The handle basis matches for MD/KS/LA/TN/IN/VA/IA. GGR uses a different basis for MD/KS/TN/IN/VA, so leave r null there. Errors seen: KS July row duplicated MD; the VA "tax" column was fiscal-year-to-date.
- **AR:** DFA publishes only combined casino + sports receipts (no handle), so Arkansas updates only from the vendor file.
- **Blocked or unreliable:** WV Lottery sites (CloudFront), IL Gaming Board app, KY Tableau, WY reports in Google Drive. For these, rely on the vendor file or rg.org.

### Cadence
NY weekly (posts Thu/Fri). Most regulators publish monthly, 10 to 25 days after month-end. AZ/IL/KY/CO/MO run about 6 to 8 weeks behind. The vendor file arrives roughly monthly.

## Update procedure

1. Read `data/meta.json` (last snapshot) and the end of `refresh-log.md`.
2. Research what changed since the snapshot date, plus every item marked pending, following the tracker-specific instructions.
3. Edit the relevant `data/*.json` files (shapes and accuracy rules above).
4. `python scripts/set_snapshot.py` - sets the snapshot date to today.
5. `python scripts/new_links.py --check` - exit 0 = fine; exit 1 = fix links reported `broken` (a `blocked` 401/403/429 is common for news sites - keep only if it came from your searches); exit 2 = no network, the check proves nothing, so keep only search-result URLs and write "links unchecked" in the log.
6. `python scripts/build_standalone.py` - regenerates `OSB_iGaming_National_Tracker.html`.
7. `python scripts/validate.py` - must print `VALIDATION PASSED`. Never commit a failing state.
8. Append to `refresh-log.md`: `- **YYYY-MM-DD** (Claude Code): <verified changes, naming sources>. Unconfirmed: <items>. Checked, no change: <items>. Snapshot -> <label>.` If nothing changed, still set the snapshot date and log "no verified changes".
9. Commit `Data refresh YYYY-MM-DD: <summary>` and push (to the branch the routine prompt or the user names; a one-off request without one -> ask, or open a pull request).
10. Finish with a short summary: verified changes with sources, unconfirmed items, links you could not verify.

For a one-off request ("add this ruling", "make the table sortable"): make the change, then steps 6-9.

## Do not

- Edit `OSB_iGaming_National_Tracker.html` by hand, or move code out of the `data-tracker-app` blocks.
- Delete rows to "tidy up" without a stated reason in the log.
- Commit when `validate.py` fails.
- Add CI workflows or publishing unless the owner asks.
