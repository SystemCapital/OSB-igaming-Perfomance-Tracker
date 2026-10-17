# CLAUDE.md - maintaining "US iGaming & OSB National Tracker"

This repository holds a tracker dashboard. Claude Code (often a scheduled routine) keeps its data current. Read this whole file before changing anything.

## Repository map

| Path | What it is | Edit? |
|---|---|---|
| `data/*.json` | ALL tracker data, one file per dataset (table below) | Yes - updates change these |
| `data/meta.json` | Title, snapshot date shown on the page, build file name | Date only via `scripts/set_snapshot.py` |
| `data/schema.json` | Validation rules inferred at conversion | Only to add a new dataset or field rule |
| `index.html` | Dashboard page. Its code runs from `<script type="text/plain" data-tracker-app>` blocks after a small loader fetches `data/*.json` | Only for requested design changes |
| `OSB_iGaming_National_Tracker.html` | Ready-to-open single-file build (data + libraries embedded). Also the Claude artifact: its code runs as ordinary inline scripts, not injected at runtime like `index.html`'s loader, because sandboxes with a nonce-based Content-Security-Policy (such as Claude artifacts) can refuse injected scripts | Never by hand - run `scripts/build_standalone.py` |
| `vendor/` | Third-party libraries used by the page (with licences) | No |
| `scripts/validate.py` | Checks data shape, sources, page scripts, build freshness, render | No |
| `scripts/build_standalone.py` | Regenerates `OSB_iGaming_National_Tracker.html` | No |
| `scripts/set_snapshot.py` | Sets the snapshot date | No |
| `scripts/new_links.py` | Lists / checks source URLs added since the last commit | No |
| `scripts/render_check.js` | Simulated-browser smoke test used by validate.py | No |
| `refresh-log.md` | Audit trail - one line per update | Append only |

Scripts need Python 3.9+ (standard library only). Node.js enables the page-script and render checks.

**Error log.** The first `<script data-tracker-diagnostics>` block in `index.html` lists script errors, scripts blocked by a Content-Security-Policy, failed loads and `console.error` calls in a red panel at the bottom of the page, and notes when no KPI cards have been drawn 8 seconds after opening. If the user reports the page or artifact "not working", ask them to press **Copy** on that panel and paste the log. Don't remove it.

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
2. **NY weekly:** add every week posted after the last week in `DETAILED_NYW`. NYSGC posts a week on the Friday after it ends, in the New York morning (week ending 11 Oct 2026: Friday 16 Oct, 10:37 to 10:45am New York time). Say in the summary which week it's current to.
3. Pull newly published months from the sources below. Reconcile operator sums to statewide totals.
4. If a new `Full Dataset <Mon YY>.xlsx` exists (it sits outside this repo; the user supplies it), overwrite every state-month it covers in RAW and rebuild DET_OSB from it. Keep regulator months beyond its coverage. Then run the post-load checks: PA iLottery fix; **dropout check** (any licensee/brand over $3M the prior month that goes to 0 while the state still reports = vendor gap, so don't load it; e.g. WV Mardi Gras online, Jun to Aug 2026); scan for negative `p` or federal-only `t` (e.g. CO 2026-06); **Nebraska:** the vendor's NE handle is 10 × GGR, a made-up figure, and its tax adds 0.25% of that handle, so set NE `h` to null and `t` to 20% of `r` in RAW and DET_OSB.

### Sources (verified)

**Fetching.** These rules were checked on 14 Oct 2026 from the routine's environment.
- **User agent.** Send a full browser user agent with Accept headers: `curl -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36" -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" -H "Accept-Language: en-US,en;q=0.9"`. CO, MD, MI, MS, MT, NJ, NC, OH and VT refuse curl's default agent, a bare `Mozilla/5.0`, or both.
- **Exception: gaming.ny.gov.** It returns 403 to the browser agent, so use curl's default agent there.
- **File links.** Open the report page below and take the file link from it. File names, upload folders and media ids change month to month, so build a URL only where the table says the URL can be built.
- **Check the file.** Some hosts return 200 with an HTML page for a file that doesn't exist (MS, OH, VA). Check the signature (`%PDF`; `PK` for xlsx and zip) and the month named inside the file.
- **Blanks.** A blank or "-" month means not reported, not zero.

**Report pages** (every state in RAW; FY = fiscal year)

| State | Report page | File and what it holds |
|---|---|---|
| AZ | https://gaming.az.gov/resources/reports | **Blocked:** Cloudflare returns 403 to curl and to WebFetch on every path. Files were `EW Website Report-<Month> <YYYY> UNAUDITED.pdf`. Use the vendor file or rg.org. ADG press-release figures are interim. |
| AR | https://www.dfa.arkansas.gov/office/taxes/excise-tax-administration/miscellaneous-tax/arkansas-miscellaneous-tax-laws/casino-gaming-sports-wagering/ | `CasinoGamingFYE<FY>_<Month>.pdf` holds combined casino + sports state receipts only: no handle, no GGR. Use the vendor file only. |
| CO | https://sbg.colorado.gov/sports-betting-monthly-reports | `<seq> Monthly Summary (<Month> '<YY>).pdf`. The sequence number and suffix vary, so take the link. Holds retail/online/total GGR, net sports betting proceeds and tax. Handle = Total row of the top-10 sports wagers table, where parentheses are not negatives. The free-bet deduction ended 1 Jul 2026. Needs the browser agent. |
| CT | OSB https://data.ct.gov/resource/xf6g-659c.json; iGaming https://data.ct.gov/resource/imqd-at3c.json | Socrata API (use `curl -g`). Latest month: `?$select=max(month_ending)`. One month: `?$where=month_ending='YYYY-MM-DDT00:00:00.000'` (last day of the month). Fields: wagers, patron_winnings, promotional_deduction_*, tax_payment_*. |
| DE | OSB https://www.delottery.com/Sports-Lottery/Sportsbooks/Monthly-Proceeds-And-Distribution-Financial-Year/<FY>; iGaming https://www.delottery.com/More/iGaming/Revenue-Distribution/Monthly-Proceeds-And-Distribution-Financial-Year/<FY> | HTML tables. FY = July to June, named by its end year: 2027 = Jul 2026 to Jun 2027. OSB uses 4- and 5-week accounting periods, not calendar months. |
| DC | https://dclottery.com/olg/financials | Month page `https://dclottery.com/olg/financials/<month>-<yyyy>-unaudited` (can be built). Per-operator HTML tables with no statewide total, so sum the operators. Negatives are in parentheses. olg.dc.gov returns 502. |
| IL | https://igb.illinois.gov/sports-wagering/sports-reports.html, which leads to the app https://igbapps.illinois.gov/SportsReports_AEM.aspx | ASP.NET form, three steps:<br>1. GET the app page. Keep its cookies and its `__VIEWSTATE`, `__VIEWSTATEGENERATOR` and `__EVENTVALIDATION` fields.<br>2. POST those back with `SearchStartMonth`, `SearchStartYear`, `SearchEndMonth`, `SearchEndYear`, `ViewType=ViewCSV`, `ButtonSearch.x=12` and `ButtonSearch.y=8`.<br>3. Add the report type: `SearchType=TypeAccrual&SearchAccrual=Tax Summary Report` for AGR and tax, or `SearchType=TypeCash&SearchCash=Detail Report` for handle. `SearchCash` must hold a valid option even in accrual mode.<br>"No revenue results" = the month is not out yet. |
| IN | https://www.in.gov/igc/publications/monthly-revenue/ | `https://www.in.gov/igc/files/reports/<YYYY>/<YYYY>-<MM>-Revenue.xlsx` (can be built). Sheet "7 SW Tax Summary" has handle, sports wagering AGR and tax; "8 SW Details" splits them by skin. No promos. |
| IA | https://irgc.iowa.gov/publications-reports/sports-wagering-revenue | Link "<Month> <YYYY> Sports Wagering Revenue" goes to `/media/<id>/download` (the id changes). Handle, payouts, net receipts and state tax by casino, retail + internet. Also check the "FY <YYYY> Sports Wagering Revenue Amendments" file. |
| KS | https://www.kslottery.gov/publications/sports-monthly-detail-breakdown/ (summary: /publications/sports-monthly-revenues/) | `/media/<token>/sports-wagering-monthly-detail-YYYY-MM.pdf` (the token changes). Settled wagers, prizes, promotional deductions, FET, net revenues and state share. Unaudited. |
| KY | https://khrc.ky.gov/newstatic_info.aspx?static_ID=694 | Tableau only, and it shows **only the latest month**, so load each month while it is shown.<br>Image: `https://public.tableau.com/views/SportsWageringMarketReport/SWStory.png?:showVizHome=no&:size=1600,1000`; read the figures from it. Handle, winnings, FET, approximate AGR and excise tax by licensee.<br>New-month check: `lastPublishDate` at `https://public.tableau.com/profile/api/single_workbook/SportsWageringMarketReport`. |
| LA | https://lsp.org/about/leadershipsections/bureau-of-investigation/gaming-enforcement-division/gaming-revenue-reports/ | `/media/<token>/fy<FY>_mobile_sb_YYYY_MM.xlsx` and `…_retail_sb_…` (separators vary, so take the links). Sum mobile + retail: wagers written, promo deductions, net proceeds, taxes paid. |
| ME | https://www.maine.gov/dps/gcu/sports-wagering/sports-wagering-revenue | One cumulative calendar-year PDF per licensee: Passamaquoddy, Penobscot Maliseet Micmac, Oxford Sportsbook, First Tracks. Sum all four. Wagers, voids, payouts, FET, AGR, 10% tax. |
| MD | https://www.mdgaming.com/maryland-sports-wagering/revenue-reports/ | Go from the page to the monthly release, then to `wp-content/uploads/<pubYYYY>/<pubMM>/<Month>-<YYYY>-Sports-Wagering-Data.xlsx`. The folder is the publication month, not the data month. Handle, prizes, promotional play, other deductions and taxable win by licensee. Needs the browser agent with Accept headers. |
| MA | https://massgaming.com/regulations/revenue/ | `https://massgaming.com/wp-content/uploads/MGC-Revenue-Report-<Month>-<YYYY>.pdf`. Cat. 1 retail + Cat. 3 online wagers (handle), win, taxable revenue and tax. Out around the 15th. |
| MI | https://www.michigan.gov/mgcb/detroit-casinos/resources/revenues-and-wagering-tax-information | `https://www.michigan.gov/mgcb/-/media/Project/Websites/mgcb/Detroit-Casino-Revenue-Files/Internet-Sports-Betting---<YYYY>.xlsx` and `…/Internet-Gaming---<YYYY>.xlsx`; the layout is in the MI notes below. Online only: Detroit retail sports is in `Detroit_Casino_RSB-<YYYY>-PDF.pdf`. Needs the browser agent. |
| MS | https://www.msgamingcommission.com/reports/monthly_reports | `https://www.msgamingcommission.com/files/monthly_reports/<MMYY>_sports_wagering.xlsx` (can be built). Row "Overall for State": write (handle) and taxable revenue. Retail only. A missing month returns 200 with an HTML page. |
| MO | https://www.mgc.dps.mo.gov/SportsWagering/sw_financials/rb_SWFin_main.html | `FY<YY>_SWFinReport/<MM>_<Mon>/SW Monthly Financials <MMYY>.xlsx`. FY starts in July and the spacing varies, so take the link. Handle, deductions, taxable AGR and tax per licensee, retail + mobile. |
| MT | https://montanalottery.com/news/ | Weekly press releases only, and the weeks cross month ends, so there is no official monthly figure. Use the vendor file or rg.org. |
| NE | https://nrgc.nebraska.gov/gaming/reports | PDF "<YYYY> Gaming Tax Revenue Breakdown". The revision suffix changes, so take the link. Sports betting GGR per property; sum every property. Retail only. No handle is published, so store `h` = null. `t` = 20% of sports GGR, the state rate the report applies to all GGR. There is no federal excise, because it needs a handle. |
| NV | https://www.gaming.nv.gov/about-us/gaming-revenue-information-gri/ | `monthly-revenue-report---<month>-<yyyy>.pdf`. The hyphen count and folder vary, so take the link. Sports Pool win in thousands; no handle. |
| NH | https://www.nhlottery.com/About-Us/Financial-Reports | `Sports_Betting_Summary_FY<YY>.pdf`, hosted on Contentful, so take the link. |
| NJ | OSB https://www.njoag.gov/about/divisions-and-offices/division-of-gaming-enforcement-home/financial-and-statistical-information/monthly-sports-wagering-revenue-reports/; iGaming https://www.njoag.gov/about/divisions-and-offices/division-of-gaming-enforcement-home/financial-and-statistical-information/monthly-internet-gross-revenue-reports/ | Tax returns: `https://www.nj.gov/oag/ge/docs/Financials/SWRTaxReturns/<YYYY>/<Month><YYYY>.pdf` (OSB) and `…/IGRTaxReturns/<YYYY>/<Month><YYYY>.pdf` (iGaming). Handle: `…/PressRelease<YYYY>/<Month><YYYY>.pdf`. Release dates: `…/PressReleaseDates/pressreleasedates<YYYY>.pdf`. Needs the browser agent. |
| NY | https://gaming.ny.gov/revenue-reports | `https://gaming.ny.gov/<slug>-weekly-report-excel` and `…-monthly-report-excel`; the slugs are in the NY notes below. They redirect to `/system/files/documents/<YYYY>/<MM>/…`. Use curl's default agent only. The monthly sheets date each month on day 3. |
| NC | https://ncgaming.gov/reports/ | `https://ncgaming.gov/wp-content/uploads/<YYYY>/<MM>/NCSLC-Sports-Betting-Revenue-Report-<Month>-<YYYY>.pdf`. The name changes (June 2026 was `NCSLC-Monthly-Revenue-Report-June-2026.pdf`), so take the link. Needs the browser agent. |
| OH | https://casinocontrol.ohio.gov/about/revenue-reports | `https://dam.assets.ohio.gov/raw/upload/casinocontrol.ohio.gov/revenue-reports/<YYYY>/Sports/<YYYY>_Sports_Gaming_Revenue_Report<MM>.xlsx`; a 404 there = the month is not out yet. The revenue page returns 200 even for a wrong path, so check that it lists dam.assets.ohio.gov links. Needs the browser agent. |
| OR | https://www.oregonlottery.org/about/how-we-operate/commission-and-director-info/ | The "Comparison Sales Report" in the commission meeting packets gives fiscal-year-to-date sports turnover, for a handle cross-check only. There is no official GGR on the tracker's basis, and rg.org's Oregon table doesn't match the tracker either. Use the vendor file only. |
| PA | https://gamingcontrolboard.pa.gov/news-and-transparency/revenue?field_gaming_revenue_fiscal_year_target_id=292 | Fiscal-year filter ids: 292 = FY26/27, 285 = FY25/26; read a new year's id from the page's filter. Files are `https://gamingcontrolboard.pa.gov/sites/default/files/<YYYY-MM>/FY26-27 Monthly Sports Wagering Report Summary.xlsx` and `…Interactive Gaming Report Summary.xlsx`. The folder changes, so take the link. www.pgcb.pa.gov fails. |
| RI | https://www.rilot.com/en-us/about-us/financials.html | `https://www.rilot.com/content/dam/interactive/ilottery/pdfs/financial/SportsbookSummaryFY<YYYY>.pdf` and `…/iGamingWebsiteDataFY<YYYY>.pdf`. FY = July to June, named by its end year. "-" = not reported yet. |
| SD | https://dor.sd.gov/businesses/gaming/ | `/media/<id>/<month>-<yyyy>-monthly-statistics.pdf`. The id varies, so take the link. Handle and win from the "Sports Wagering" block. Deadwood retail only. |
| TN | https://www.tn.gov/swac/reports.html | `https://www.tn.gov/content/dam/tn/swac/documents/report/<YYYY>/Monthly_Report_for_SWC-<Month><YYYY>(UA).csv`. The suffix varies, so take the link. Gross wagers, adjustments, gross handle and privilege tax; no GGR. Encoded in ISO-8859-1. |
| VT | https://liquorandlottery.vermont.gov/monthly-sports-wagering-reports-2026 (each year has its own page, linked from /monthly-reports) | `https://liquorandlottery.vermont.gov/sites/liqlot/files/documents/SW_Exec_Sum_Rpt_<Month>_<YYYY>.pdf`. Handle, payouts, voids/tax/promo and AGR. Needs the browser agent. |
| VA | https://rga.lis.virginia.gov/Published/<YYYY>/RD<nnn> | Virginia Lottery's monthly letter (Jul 2026 = RD532, Aug 2026 = RD621); the PDF is at `…/RD<nnn>/PDF`. RD numbers can't be predicted: step up from the last known number and match the title "Virginia Lottery <Month> <YYYY> Sports Betting Report", skipping the lottery-sales reports. A number that doesn't exist returns 200 with "Invalid Report". valottery.com draws its pages with script, so curl gets nothing there. |
| WV | https://business.wvlottery.com/resourcesPayments | The links "Sports Wagering Data by Skin and Casino" and "Interactive Wagering Data by Skin and Casino" give zips. Each zip holds `FY<YY> - … by Skin and Casino.xlsx` with tickets sold (handle) and taxable revenue per casino and skin; sum the skins. Not blocked. |
| WY | https://gaming.wyo.gov/revenue-reports/financial-reports/combined-wagering-activity-reports | One Google Drive file per month, `https://drive.google.com/uc?export=download&id=<id>`. It is served as octet-stream, so check that it starts with `%PDF`. The "ONLINE SPORTS WAGERING" section has monthly wagers, GGR and taxable gaming revenue per operator, plus a total. |

**How to read the main states**
- **NY OSB:** gaming.ny.gov weekly and monthly Excel per operator. Slugs:
  - `/fanduel-…`, `/draftkings-sport-book-…`, `/fanatics-…`, `/betmgm-…`, `/caesars-sport-book-…`, `/ballybet-…`
  - `/rush-street-interactive-…` = BetRivers; `/resorts-world-bet-…` = Resorts World
  - `/wynn-interactive-…` = ESPN Bet (its files now carry the theScore Bet name; keep it stored as ESPN Bet)
  - Each slug ends in `weekly-report-excel` or `monthly-report-excel`. Statewide: `/statewide-sports-wagering-monthly-report-excel`.
  - Sheets are by fiscal year ("FY 26-27" = April to March). The "Week-Ending" column is an Excel serial date. Use Handle and GGR.
  - Find the columns from each sheet's header row; they move (FY 21-22 has Handle in B and GGR in D, later sheets C and F).
  - The wynn-interactive file has two FY 24-25 sheets: "FY 24-25" (WynnBet, to Aug 2024) and "FY 24-25 ESPN" (ESPN Bet, from Sep 2024). Add both into ESPN Bet.
  - Store whole dollars, rounded from the file's cents. Operator weeks must add up to `/statewide-sports-wagering-weekly-report-excel` (within $2 of rounding).
- **CT:** Socrata API data.ct.gov `imqd-at3c` (iGaming), `xf6g-659c` (OSB). r = wagers − patron_winnings. Operators: MPI + MPTN = DraftKings, Mohegan Digital + Tribe = FanDuel, CT Lottery = PlaySugarHouse.
- **NJ:** DGE `nj.gov/oag/ge/docs/Financials/IGRTaxReturns/<YYYY>/<Month><YYYY>.pdf` is iGaming: per-skin "SKIN DETAIL" pages, with line 3 win, line 11 tax and line 12 promos. OSB revenue is in `SWRTaxReturns/...` (lines 3 + 16); handle comes from the DGE press release. **Always confirm the "FOR THE MONTH OF" header**: file naming has shifted between publication month and data month.
- **PA:** PGCB revenue page at gamingcontrolboard.pa.gov (www.pgcb.pa.gov fails). Use the FY files (`FY26-27 Monthly Interactive Gaming Report Summary.xlsx`, `…Sports Wagering…`). Files move to new dated folders, so **always re-scrape the link**.
  - Operator = ALL-CAPS row; allow `!`, as in LIVE! PHILADELPHIA.
  - Sum "Wagers Received", and "Gross Revenue" + "Revenue (Rake…)".
  - Sports: use the GRAND TOTAL > Total Sports Wagering block.
- **MI:** MGCB `Internet-Gaming---<YEAR>.xlsx` (stride 3: Gross, AGR, state tax; p = Gross − AGR) and `Internet-Sports-Betting---<YEAR>.xlsx` (stride 4: handle, gross, AGR, tax). Name map: theScore Bet = Hollywood, NeoGames = Firekeepers, Strive = Eagle, GAN = Four Winds, Caesars/WSOP = Caesars, Bet365 = bet365, BetPARX = betParx.
- **DE:** delottery.com FY pages (table above); single operator, BetRivers. iGaming: h = table + video bets; r = (bets − win) for tables and video, + poker; p = promo deductions; n = Total NGR.
- **RI:** rilot.com financials PDFs `SportsbookSummaryFY<YYYY>.pdf` and `iGamingWebsiteDataFY<YYYY>.pdf`. About a 3-week lag.
- **OH:** `<YYYY>_Sports_Gaming_Revenue_Report<MM>.xlsx` (table above). Row "Total Online and Retail" gives h, r and p; promos are NOT deductible. t = 0.25%·h + 20%·taxable.
- **VA:** Virginia Lottery letters to the Governor (table above). h = total wagers; r = wagers − winnings, not AGR; t = that month's 15% tax + 0.25%·h.
- **NC:** single statewide row in the monthly report (FY July to June). The tracker's basis, used for every month since 2024-03:
  - h = Total Wagering Revenue − Cancelled/Void Wagers (net of voids, not the Total column alone).
  - r = Gross Wagering Revenue; p = Promo Wagering Revenue; n = r − p.
  - t = Estimated Tax Proceeds + 0.25%·h. The state rate is 18% to Jun 2026 and 23% from Jul 2026.
- **NV:** Sports Pool win only (in thousands); handle is not in the report.
- **rg.org/statistics/us/<state>** tables copy regulator figures.
  - The handle basis matches the tracker for MD/KS/LA/TN/IN/VA/IA.
  - GGR is on a different basis for MD/KS/TN/IN/VA, so leave r null there.
  - Errors seen: the KS July row duplicated MD; the VA "tax" column was fiscal-year-to-date.
- **No usable official monthly source:** update these from the vendor file, or from rg.org as interim where its basis matches.
  - AZ: Cloudflare blocks this environment.
  - AR: receipts only.
  - MT: weekly releases only.
  - OR: no GGR on the tracker's basis.
  - WV, IL, KY and WY were listed as blocked before 14 Oct 2026; all four are reachable now (table above).

### Cadence
NY weekly (posts Friday morning New York time). Most regulators publish monthly, 10 to 25 days after month-end. AZ/IL/KY/CO/MO run about 6 to 8 weeks behind. The vendor file arrives roughly monthly.

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
