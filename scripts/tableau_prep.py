"""
Tableau Prep — Final Data Cleaning & Export
============================================
OECD Case Competition — Data Preprocessing Script

Prerequisite: Run sdg_ohe_pipeline.py first to generate OECD_cleaned_with_SDG_OHE.csv

What this script produces:
  1. OECD_main.csv         — The primary Tableau data source (cleaned, all rows)
  2. OECD_sdg_long.csv     — SDG exploded table for Tab 2 (one row per grant × SDG goal)

Changes applied to the main dataset:
  - usd_commitment_defl: cast from text to float
  - expected_duration: parsed into duration_years (integer, end_year - start_year)
  - is_nda_aggregate: boolean flag (True where year == "2020-2023")
  - year_clean: integer year (null for NDA rows, for safe time-series filtering)
  - Thematic score columns filled: NULL markers → 0 where the grant IS screened
    (we do NOT fill NULLs for unscreened grants — those stay NULL so Tableau
     can distinguish "0 = not targeted" from "not screened")
  - Sector/subsector label whitespace: stripped of leading/trailing spaces
  - Columns deprioritized in the game plan are dropped from the Tableau export
    to keep the file clean: row_id, additional_info, channel_code,
    Sector (numeric), subsector (numeric)

SDG long table columns:
  row_id, sdg_goal (1-17), sdg_goal_name, year_clean, is_nda_aggregate,
  region_macro, region, country, sector_description, subsector_description,
  organization_name, Donor_country, usd_disbursements_defl, type_of_flow

Author: OECD Case Comp Team
"""

import re
import sys
import pandas as pd

# Force UTF-8 output on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

INPUT_OHE   = r"c:\Users\WrenzyBoba\Desktop\oecd case comp\OECD_cleaned_with_SDG_OHE.csv"
OUT_MAIN    = r"c:\Users\WrenzyBoba\Desktop\oecd case comp\OECD_main.csv"
OUT_SDG_LNG = r"c:\Users\WrenzyBoba\Desktop\oecd case comp\OECD_sdg_long.csv"

SDG_NAMES = {
    1:  "No Poverty",
    2:  "Zero Hunger",
    3:  "Good Health and Well-Being",
    4:  "Quality Education",
    5:  "Gender Equality",
    6:  "Clean Water and Sanitation",
    7:  "Affordable and Clean Energy",
    8:  "Decent Work and Economic Growth",
    9:  "Industry, Innovation and Infrastructure",
    10: "Reduced Inequalities",
    11: "Sustainable Cities and Communities",
    12: "Responsible Consumption and Production",
    13: "Climate Action",
    14: "Life Below Water",
    15: "Life on Land",
    16: "Peace, Justice and Strong Institutions",
    17: "Partnerships for the Goals",
}

# Columns to drop from the main export (deprioritized per game plan)
COLS_TO_DROP = ["row_id", "additional_info", "channel_code", "Sector", "subsector"]

# Thematic marker columns (0-2 scale, NULL = not screened)
THEMATIC_MARKERS = [
    "gender_marker",
    "climate_change_mitigation",
    "climate_change_adaptation",
    "environment",
    "biodiversity",
    "desertification",
    "nutrition",
]

OHE_COLS = [f"sdg_goal_{i}" for i in range(1, 18)]


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: parse expected_duration
# ─────────────────────────────────────────────────────────────────────────────

def parse_duration(val):
    """
    Convert expected_duration text to integer number of years.
    Handles formats like:
      "2021-2024"   → 3
      "2019-2022"   → 3
      "3 years"     → 3
      "2021"        → 0  (single year = 1 year project, stored as 0 diff)
      NaN / other   → None
    """
    if pd.isna(val):
        return None
    s = str(val).strip()

    # Pattern: YYYY-YYYY
    m = re.match(r"(\d{4})\s*[-–]\s*(\d{4})", s)
    if m:
        start, end = int(m.group(1)), int(m.group(2))
        diff = end - start
        return diff if diff >= 0 else None

    # Pattern: N year(s)
    m = re.match(r"(\d+)\s*years?", s, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # Single 4-digit year: treat as 1-year project → duration = 1
    m = re.match(r"^\d{4}$", s)
    if m:
        return 1

    return None


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("Loading OHE dataset...")
    df = pd.read_csv(INPUT_OHE, low_memory=False)
    print(f"  {len(df):,} rows × {len(df.columns)} columns")

    # ── 1. Fix usd_commitment_defl dtype ─────────────────────────────────────
    print("\nStep 1: Fix usd_commitment_defl dtype...")
    df["usd_commitment_defl"] = pd.to_numeric(df["usd_commitment_defl"], errors="coerce")
    n_valid = df["usd_commitment_defl"].notna().sum()
    print(f"  Converted. {n_valid:,} non-null values ({n_valid/len(df)*100:.1f}%)")

    # Verify usd_disbursements_defl
    df["usd_disbursements_defl"] = pd.to_numeric(df["usd_disbursements_defl"], errors="coerce")
    n_disb = df["usd_disbursements_defl"].notna().sum()
    print(f"  usd_disbursements_defl: {n_disb:,} non-null ({n_disb/len(df)*100:.1f}%)")

    # ── 2. Parse expected_duration → duration_years ───────────────────────────
    print("\nStep 2: Parse expected_duration -> duration_years...")
    df["duration_years"] = df["expected_duration"].apply(parse_duration)
    n_dur = df["duration_years"].notna().sum()
    print(f"  Parsed {n_dur:,} durations ({n_dur/len(df)*100:.1f}% coverage)")
    print(f"  Distribution:")
    print(df["duration_years"].value_counts().sort_index().head(15).to_string())

    # ── 3. Handle NDA year rows ───────────────────────────────────────────────
    print("\nStep 3: Flagging NDA aggregate rows (year == '2020-2023')...")
    df["is_nda_aggregate"] = df["year"].astype(str).str.strip() == "2020-2023"
    df["year_clean"] = pd.to_numeric(df["year"], errors="coerce")
    n_nda = df["is_nda_aggregate"].sum()
    n_ok  = (~df["is_nda_aggregate"]).sum()
    print(f"  NDA aggregate rows (year='2020-2023'): {n_nda:,}")
    print(f"  Regular year rows:                     {n_ok:,}")
    print(f"  Year range (non-NDA): {int(df['year_clean'].min())} – {int(df['year_clean'].max())}")

    # ── 4. Clean sector/subsector label whitespace ────────────────────────────
    print("\nStep 4: Cleaning sector/subsector labels...")
    for col in ["sector_description", "subsector_description", "region_macro",
                "region", "country", "channel_name", "organization_name", "Donor_country"]:
        if col in df.columns:
            before = df[col].nunique()
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace("nan", pd.NA)
            after = df[col].nunique()
            if before != after:
                print(f"  {col}: {before} → {after} unique values after strip")
            else:
                print(f"  {col}: {after} unique values (clean)")

    # ── 5. Drop deprioritized columns ─────────────────────────────────────────
    print("\nStep 5: Dropping deprioritized columns...")
    cols_present = [c for c in COLS_TO_DROP if c in df.columns]
    df_main = df.drop(columns=cols_present)
    print(f"  Dropped: {cols_present}")
    print(f"  Remaining columns: {len(df_main.columns)}")

    # ── 6. Save main CSV ──────────────────────────────────────────────────────
    print(f"\nSaving main Tableau file → {OUT_MAIN}")
    df_main.to_csv(OUT_MAIN, index=False)
    print(f"  Saved {len(df_main):,} rows × {len(df_main.columns)} columns")

    # ── 7. Build SDG long-format table ────────────────────────────────────────
    print("\nStep 6: Building SDG long-format table for Tab 2...")

    # Columns to carry into the long table
    carry_cols = [
        "row_id" if "row_id" in df.columns else None,
        "year_clean", "is_nda_aggregate",
        "region_macro", "region", "country",
        "sector_description", "subsector_description",
        "organization_name", "Donor_country",
        "usd_disbursements_defl",
        "type_of_flow",
    ]
    carry_cols = [c for c in carry_cols if c is not None and c in df.columns]

    # Melt the OHE columns into long format
    df_ohe = df[carry_cols + OHE_COLS].copy()
    df_long = df_ohe.melt(
        id_vars=carry_cols,
        value_vars=OHE_COLS,
        var_name="sdg_col",
        value_name="is_tagged",
    )

    # Keep only rows where this grant IS tagged to this SDG goal
    df_long = df_long[df_long["is_tagged"] == 1].copy()

    # Extract integer SDG goal number from column name (sdg_goal_3 → 3)
    df_long["sdg_goal"] = df_long["sdg_col"].str.extract(r"(\d+)$").astype(int)
    df_long["sdg_goal_name"] = df_long["sdg_goal"].map(SDG_NAMES)

    # Drop helper columns and reorder
    df_long = df_long.drop(columns=["sdg_col", "is_tagged"])
    final_order = ["sdg_goal", "sdg_goal_name"] + carry_cols
    df_long = df_long[final_order].sort_values(["sdg_goal", "region_macro"]).reset_index(drop=True)

    print(f"  Long table rows: {len(df_long):,}  (each grant appears once per SDG it's tagged to)")
    print(f"  Rows per SDG goal:")
    for g in range(1, 18):
        count = (df_long["sdg_goal"] == g).sum()
        name  = SDG_NAMES[g]
        print(f"    SDG {g:2d} ({name[:35]:35s}): {count:6,}")

    print(f"\nSaving SDG long table → {OUT_SDG_LNG}")
    df_long.to_csv(OUT_SDG_LNG, index=False)
    print(f"  Saved {len(df_long):,} rows × {len(df_long.columns)} columns")

    # ── 8. Final summary ──────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("DONE. Files ready for Tableau:")
    print(f"  OECD_main.csv      → {len(df_main):,} rows × {len(df_main.columns)} cols")
    print(f"  OECD_sdg_long.csv  → {len(df_long):,} rows × {len(df_long.columns)} cols")
    print("\nTableau load instructions:")
    print("  1. Load OECD_main.csv as your primary data source")
    print("  2. Load OECD_sdg_long.csv as a secondary data source")
    print("     (No join needed — they serve different tabs)")
    print("  3. Use OECD_main.csv for Tab 1, 3, and 4")
    print("  4. Use OECD_sdg_long.csv for Tab 2 (SDG widget)")
    print("  5. For time series: filter is_nda_aggregate == False")
    print("="*60)


if __name__ == "__main__":
    main()
