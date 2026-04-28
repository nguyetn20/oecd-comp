# OECD Case Competition — Scripts & Data Context

## Project Overview
This is a case competition dashboard project for the OECD (Organisation for Economic Co-operation and Development).
The client uses UN Sustainable Development Goal (SDG) language. The team is building a 4-tab Tableau dashboard.

**Input file:** `OECD Dataset.xlsx` (sheet: `complete_p4d3_df`)
- 116,561 rows, 32 columns
- Every row = one philanthropic grant transaction
- Key money column: `usd_disbursements_defl` (inflation-adjusted USD millions, 2023 constant)

**Main output file:** `OECD_cleaned_with_SDG_OHE.csv`
- Same 116,561 rows + 17 new OHE columns: `sdg_goal_1` through `sdg_goal_17`
- This is the file to load into Tableau

---

## Tableau-Ready Output Files

| File | Rows | Cols | Used For |
|---|---|---|---|
| `OECD_main.csv` | 116,561 | 47 | Tabs 1, 3, 4 |
| `OECD_sdg_long.csv` | 209,650 | 14 | Tab 2 (SDG widget) |

**Load order in Tableau:**
1. `OECD_main.csv` as primary data source
2. `OECD_sdg_long.csv` as secondary (no join needed — serves separate sheets)
3. For all time-series views: filter `is_nda_aggregate == False`

**Why two files?**
- `OECD_main.csv` keeps one row per grant (original structure) with 17 OHE columns (`sdg_goal_1`–`sdg_goal_17`) — good for Tab 1 funding totals, Tab 3 donor analysis, Tab 4 FAI score
- `OECD_sdg_long.csv` is "exploded" long format — one row per (grant × SDG goal) — lets Tableau directly `SUM(usd_disbursements_defl)` grouped by `sdg_goal` for the SDG grid and bubble chart

**On the 1,802 all-zero OHE rows:** Do NOT drop them from `OECD_main.csv` — they still have valid funding amounts for Tab 1/3/4. They are naturally absent from `OECD_sdg_long.csv` since no SDG rows are generated for them.

---

## Scripts

### `tableau_prep.py`
**Purpose:** Final cleaning + export of Tableau-ready files. Run AFTER `sdg_ohe_pipeline.py`.

**What it does:**
1. Fixes `usd_commitment_defl` from text to float (37.7% non-null — missing in first 30k rows by design)
2. Parses `expected_duration` text ranges → `duration_years` integer column (26.2% parsed; remainder is free text or null)
3. Adds `is_nda_aggregate` boolean flag (True for `year == "2020-2023"` rows — only 3 rows in this dataset)
4. Adds `year_clean` integer year (null for NDA rows; safe for time-series)
5. Strips whitespace from all label columns (sector, region, country, org names)
6. Drops deprioritized columns: `row_id`, `additional_info`, `channel_code`, `Sector` (numeric), `subsector` (numeric)
7. Saves `OECD_main.csv` (47 columns)
8. Melts the 17 OHE columns into long format → `OECD_sdg_long.csv` (14 columns, 209,650 rows)

**To run:**
```
python "c:\Users\WrenzyBoba\Desktop\oecd case comp\scripts\tableau_prep.py"
```

---

### `sdg_ohe_pipeline.py`
**Purpose:** SDG inference + one-hot encoding pipeline

**What it does:**
1. Loads `OECD Dataset.xlsx`
2. For rows WITH `sdg_focus` (101,337 rows / 86.9%):
   - Parses semicolon-delimited SDG target strings (e.g. `"3.1;5.6;15.2"`)
   - Floors each target to its integer SDG goal (e.g. 15.2 → 15)
   - Deduplicates → set of goal integers (e.g. {3, 5, 15})
3. For rows WITHOUT `sdg_focus` (15,224 rows / 13.1%):
   - Infers top 1-3 SDGs from `subsector` code (preferred, more targeted)
   - Falls back to `Sector` code if no subsector match
   - **1 SDG** if very targeted (e.g. "Malaria control" → SDG 3)
   - **2 SDGs** if cross-cutting (e.g. "Reproductive health" → SDG 3, 5)
   - **3 SDGs** if broad/multisector (e.g. "Multisector aid" → SDG 1, 10, 17)
   - **0s** for unallocated/unspecified sectors (no inferrable SDG)
4. One-hot encodes into 17 columns (`sdg_goal_1` through `sdg_goal_17`)
5. Saves result to `OECD_cleaned_with_SDG_OHE.csv`

**Run results (last successful run):**
- Parsed from existing sdg_focus: 101,337 rows
- Inferred from sector/subsector:  13,422 rows
- No SDG assignable (all zeros):    1,802 rows (Unallocated/Admin/Refugee admin)
- Total SDG coverage:             114,759 / 116,561 rows (98.5%)

**To run:**
```
python "c:\Users\WrenzyBoba\Desktop\oecd case comp\scripts\sdg_ohe_pipeline.py"
```

---

## SDG Mapping Logic
The mapping (`SUBSECTOR_TO_SDG` and `SECTOR_TO_SDG` dicts in the script) was built by:
1. Reading all 17 SDG goal descriptions from https://sdgs.un.org/goals
2. Extracting all unique sector/subsector codes and descriptions from the OECD dataset
3. Manually mapping each OECD CRS sector/subsector to the most relevant UN SDGs
   using the specificity rule (1 goal if narrow, 2-3 if broad)

---

## Dashboard Plan (4 Tabs in Tableau)

**Tab 1 - The Big Picture:** Global Funding Explorer
- Choropleth map, stacked bar by sector over time, top donors, KPI tiles
- Primary filters: year range, region, sector, donor country

**Tab 2 - SDG Alignment:** The SDG Widget
- 17 SDG tiles (click to filter), bubble chart, SDG x sector heatmap, SDG x region bar
- Powered by `sdg_goal_1` through `sdg_goal_17` OHE columns

**Tab 3 - Donor Deep Dive**
- Searchable donor table, donor profile panel, line graph with dropdown, flow map

**Tab 4 - Funding Index:** Funding Adequacy Index (FAI) Score
- FAI = (country-sector share) / (country overall share), tracked over time
- Inverted as Burden Score; visualized as ranked dot plot, scatter, world map

---

## Key Dataset Notes
- First ~30,043 rows are missing: `usd_commitment_defl`, `channel_*`, `environment`,
  `biodiversity`, `desertification`, `nutrition` (earlier reporting period, not an error)
- Use `usd_disbursements_defl` as the primary money metric (populated across all rows)
- `usd_commitment_defl` is stored as text — needs dtype conversion before Tableau
- `year` column has some "2020-2023" rows (NDA orgs with aggregated data) — filter out
  for time series, or treat as a separate "NDA Aggregate" bucket
- `expected_duration` is a text year range ("2021-2024") — convert to integer (end - start)
- For Tableau sector/subsector labels: always use `sector_description` and
  `subsector_description`, NOT the numeric codes

## SDG Coverage Stats (from pipeline run)
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
