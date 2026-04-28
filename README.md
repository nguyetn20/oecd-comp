# OECD Case Competition — Scripts & Data Context

## Product Website
https://nguyetn20.github.io/oecd-comp/ 

## Project Overview
We are competing in the OECD (Organisation for Economic Co-operation and Development) case competition. The client frames work using UN Sustainable Development Goal (SDG) language, and **we built a 4-tab Tableau dashboard** so policymakers and funders can explore global philanthropic funding across geography, sector, time, and SDGs.

**Input file:** `OECD Dataset.xlsx` (sheet: `complete_p4d3_df`)
- 116,561 rows, 32 columns
- Every row = one philanthropic grant transaction
- Key money column: `usd_disbursements_defl` (inflation-adjusted USD millions, 2023 constant)

**Intermediate output:** `OECD_cleaned_with_SDG_OHE.csv`
- Same 116,561 rows + 17 new OHE columns: `sdg_goal_1` through `sdg_goal_17`
- We pass this into `tableau_prep.py`; our final Tableau-ready CSVs are listed below.

---

## Tableau-Ready Output Files

| File | Rows | Cols | Used For |
|---|---|---|---|
| `OECD_main.csv` | 116,561 | ~50 (after enhancements) | Tabs 1, 3, 4 |
| `OECD_sdg_long.csv` | 209,650 | 14 | Tab 2 (SDG widget) |
| `OECD_fai.csv` | 3,808 | 13 | Tab 4 (FAI / burden) |
| `OECD_timeline.csv` | 6 | 3 | Tab 1 (timeline reference lines) |

**How we load it in Tableau:**
1. `OECD_main.csv` as our primary data source
2. `OECD_sdg_long.csv` as a secondary source (no join required — it powers different sheets)
3. `OECD_fai.csv` and `OECD_timeline.csv` as additional sources as needed
4. For all time-series views: we filter to `is_nda_aggregate == False`

**Why `OECD_main` vs `OECD_sdg_long`?**
- `OECD_main.csv` keeps one row per grant with 17 OHE columns (`sdg_goal_1`–`sdg_goal_17`) — we use it for Tab 1 funding totals, Tab 3 donor analysis, and inputs to Tab 4.
- `OECD_sdg_long.csv` is long format — one row per (grant × SDG goal) — so we can `SUM(usd_disbursements_defl)` by `sdg_goal` for the SDG grid and bubble chart.

**On the 1,802 all-zero OHE rows:** we do **not** drop them from `OECD_main.csv` — they still carry valid funding for Tabs 1/3/4. They simply do not appear in `OECD_sdg_long.csv` because no SDG rows are generated for them.

---

## Scripts (run in this order)

### 1. `sdg_ohe_pipeline.py`
**Purpose:** SDG inference + one-hot encoding. **Run this first.**

**What we do:**
1. Load `OECD Dataset.xlsx`
2. For rows **with** `sdg_focus` (101,337 rows / 86.9%):
   - Parse semicolon-delimited SDG target strings (e.g. `"3.1;5.6;15.2"`)
   - Floor each target to its integer SDG goal (e.g. 15.2 → 15)
   - Deduplicate → a set of goal integers (e.g. {3, 5, 15})
3. For rows **without** `sdg_focus` (15,224 rows / 13.1%):
   - Infer the top 1–3 SDGs from the `subsector` code (our preferred, more specific route)
   - Fall back to `Sector` if we cannot match a subsector
   - **1 SDG** when the subsector is very targeted (e.g. “Malaria control” → SDG 3)
   - **2 SDGs** when it is cross-cutting (e.g. “Reproductive health” → SDG 3, 5)
   - **3 SDGs** when it is broad / multisector (e.g. “Multisector aid” → SDG 1, 10, 17)
   - **0s** for unallocated / unspecified sectors (nothing we can infer)
4. One-hot encode into 17 columns (`sdg_goal_1` through `sdg_goal_17`)
5. Save `OECD_cleaned_with_SDG_OHE.csv`

**Our last successful run produced:**
- Parsed from existing `sdg_focus`: 101,337 rows
- Inferred from sector/subsector: 13,422 rows
- No SDG assignable (all zeros): 1,802 rows (unallocated / admin)
- Total SDG coverage: 114,759 / 116,561 rows (98.5%)

**To run:**
```
python "c:\Users\WrenzyBoba\Desktop\oecd case comp\scripts\sdg_ohe_pipeline.py"
```

---

### 2. `tableau_prep.py`
**Purpose:** Final cleaning and Tableau exports. **Run after** `sdg_ohe_pipeline.py`.

**What we do:**
1. Coerce `usd_commitment_defl` from text to float (37.7% non-null — the first ~30k rows lack it by design)
2. Parse `expected_duration` text ranges → `duration_years` (26.2% parsed; the rest is free text or null)
3. Add `is_nda_aggregate` (True where `year == "2020-2023"` — 3 rows in this dataset)
4. Add `year_clean` (null for NDA rows for safe time-series)
5. Strip whitespace on label columns (sector, region, country, org names, etc.)
6. Drop deprioritized columns: `row_id`, `additional_info`, `channel_code`, numeric `Sector`, numeric `subsector`
7. Write `OECD_main.csv` (~47 columns at this stage)
8. Melt the 17 OHE columns to long form → `OECD_sdg_long.csv` (14 columns, 209,650 rows)

**To run:**
```
python "c:\Users\WrenzyBoba\Desktop\oecd case comp\scripts\tableau_prep.py"
```

---

### 3. `final_enhancements.py`
**Purpose:** Add map-ready ISO codes, thematic score, commitment gap, and a small events table. **Run after** `tableau_prep.py`.

**What we do:** Update `OECD_main.csv` in place (adds `country_iso3`, `thematic_score`, `commitment_gap`) and write `OECD_timeline.csv` for annotation lines on Tab 1.

**To run:**
```
python "c:\Users\WrenzyBoba\Desktop\oecd case comp\scripts\final_enhancements.py"
```

---

### 4. `build_fai.py`
**Purpose:** Pre-compute the Funding Adequacy Index (FAI) and burden score for Tab 4. **Run after** `OECD_main.csv` exists (with the columns we need).

**What we do:** Read `OECD_main.csv` and write `OECD_fai.csv` (country × sector × year).

**To run:**
```
python "c:\Users\WrenzyBoba\Desktop\oecd case comp\scripts\build_fai.py"
```

---

### 5. `export_docs.py` (optional)
**Purpose:** Regenerate our data-summary Word document for documentation or the write-up. Requires `python-docx`.

**To run:**
```
python "c:\Users\WrenzyBoba\Desktop\oecd case comp\scripts\export_docs.py"
```

---

## SDG Mapping Logic
We built the mapping (`SUBSECTOR_TO_SDG` and `SECTOR_TO_SDG` in the script) by:
1. Reading all 17 SDG goal descriptions from https://sdgs.un.org/goals
2. Pulling all unique sector/subsector codes and descriptions from the OECD dataset
3. Manually assigning each OECD CRS subsector/sector to the most relevant UN SDGs using our rule: **1 goal** if narrow, **2–3** if broad

---

## Our Dashboard (4 Tableau tabs)

**Tab 1 — The Big Picture (Global Funding Explorer):**  
We use a choropleth, stacked bar by sector over time, top donors, KPIs, and filters (year, region, sector, donor). We layer in `OECD_timeline.csv` for reference events.

**Tab 2 — SDG Alignment (SDG widget):**  
17 SDG tiles, a bubble chart, SDG × sector heatmap, SDG × region — powered by the OHE columns in `OECD_main` and/or the long file `OECD_sdg_long.csv`.

**Tab 3 — Donor Deep Dive:**  
Searchable donor view, profile panel, trend lines, optional flow — from `OECD_main.csv`.

**Tab 4 — Funding Index (FAI):**  
We visualize funding adequacy vs. burden using `OECD_fai.csv` (maps, dot plots, scatter as we designed).

---

## Key Dataset Notes
- The first ~30,043 rows are missing `usd_commitment_defl`, `channel_*`, and several thematic fields (`environment`, `biodiversity`, `desertification`, `nutrition`) — that reflects an older reporting period, not a data entry mistake.
- We use **`usd_disbursements_defl`** as our primary money field (populated for all rows).
- `usd_commitment_defl` arrives as text — we convert it before analysis or Tableau.
- Some rows use `year == "2020-2023"` (NDA org aggregates); we filter those out of time series or treat them as their own bucket.
- `expected_duration` is a text year range (e.g. `"2021-2024"`) — we convert to integer years for `duration_years`.
- In Tableau we label sectors with **`sector_description`** and **`subsector_description`**, not the raw numeric codes.

## SDG Coverage (from our pipeline run)

| SDG | Description | Row Count | % of Dataset |
|-----|-------------|-----------|-------------|
| 1  | No Poverty | 13,649 | 11.7% |
| 2  | Zero Hunger | 10,149 | 8.7% |
| 3  | Good Health & Well-Being | 38,625 | 33.1% |
| 4  | Quality Education | 19,380 | 16.6% |
| 5  | Gender Equality | 17,008 | 14.6% |
| 6  | Clean Water & Sanitation | 3,628 | 3.1% |
| 7  | Affordable & Clean Energy | 1,542 | 1.3% |
| 8  | Decent Work & Economic Growth | 9,973 | 8.6% |
| 9  | Industry, Innovation & Infrastructure | 2,291 | 2.0% |
| 10 | Reduced Inequalities | 26,180 | 22.5% |
| 11 | Sustainable Cities & Communities | 3,877 | 3.3% |
| 12 | Responsible Consumption & Production | 3,213 | 2.8% |
| 13 | Climate Action | 6,632 | 5.7% |
| 14 | Life Below Water | 1,610 | 1.4% |
| 15 | Life on Land | 5,377 | 4.6% |
| 16 | Peace, Justice & Strong Institutions | 17,465 | 15.0% |
| 17 | Partnerships for the Goals | 29,051 | 24.9% |
