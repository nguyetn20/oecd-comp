"""
Funding Adequacy Index (FAI) — Pre-Computation
===============================================
OECD Case Competition — Data Preprocessing Script

FAI Formula:
  FAI = (country's share of sector funding) / (country's share of total funding)
      = (CS / S) / (C / G)

  Where (all within the same year):
    CS = total disbursements for this country in this sector
    S  = total global disbursements for this sector
    C  = total disbursements for this country across all sectors
    G  = total global disbursements across all sectors

  FAI > 1  → country receives a LARGER share of this sector's funding
             than its overall funding share would predict (over-served)
  FAI < 1  → country receives a SMALLER share (under-served)
  FAI = 1  → exactly proportionate

  Burden Score = 1 / FAI  (higher = more under-served)

  Edge cases:
    C = 0 (country has no funding that year)       → FAI = null
    S = 0 (sector has no global funding that year) → FAI = null
    FAI = 0 (CS = 0 but country + sector exist)   → Burden = null (avoid div/0)

Output: OECD_fai.csv
  One row per (country, sector_description, year_clean) combination.
  Does NOT change any existing files.

Author: OECD Case Comp Team
"""

import sys
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

INPUT_FILE  = r"c:\Users\WrenzyBoba\Desktop\oecd case comp\OECD_main.csv"
OUTPUT_FILE = r"c:\Users\WrenzyBoba\Desktop\oecd case comp\OECD_fai.csv"


def main():
    print("Loading OECD_main.csv ...")
    df = pd.read_csv(INPUT_FILE, low_memory=False)
    print(f"  {len(df):,} rows")

    # Work only on individual-year rows (exclude NDA aggregates)
    df_ts = df[df["is_nda_aggregate"] == False].copy()
    df_ts = df_ts.dropna(subset=["year_clean", "country", "sector_description", "usd_disbursements_defl"])
    df_ts["year_clean"] = df_ts["year_clean"].astype(int)

    # Exclude regional / multi-country / unspecified entries from FAI
    # (they don't represent a single country so FAI is meaningless for them)
    exclude_terms = [
        "regional", "unspecified", "GLOBAL", "Bilateral", "Ex-Yugoslavia", ";"
    ]
    mask = df_ts["country"].apply(
        lambda x: not any(t.lower() in str(x).lower() for t in exclude_terms)
    )
    df_ts = df_ts[mask]
    print(f"  Working rows (country-level, time-series): {len(df_ts):,}")

    # ── Step 1: Build aggregation blocks ─────────────────────────────────────

    # CS = country × sector × year
    cs = (
        df_ts.groupby(["country", "country_iso3", "sector_description", "year_clean"])["usd_disbursements_defl"]
        .sum()
        .reset_index()
        .rename(columns={"usd_disbursements_defl": "cs_funding"})
    )

    # C = country × year total
    c_total = (
        df_ts.groupby(["country", "year_clean"])["usd_disbursements_defl"]
        .sum()
        .reset_index()
        .rename(columns={"usd_disbursements_defl": "c_funding"})
    )

    # S = sector × year global total
    s_total = (
        df_ts.groupby(["sector_description", "year_clean"])["usd_disbursements_defl"]
        .sum()
        .reset_index()
        .rename(columns={"usd_disbursements_defl": "s_funding"})
    )

    # G = global × year total
    g_total = (
        df_ts.groupby(["year_clean"])["usd_disbursements_defl"]
        .sum()
        .reset_index()
        .rename(columns={"usd_disbursements_defl": "g_funding"})
    )

    # ── Step 2: Join everything onto the CS grain ─────────────────────────────
    fai = cs.merge(c_total, on=["country", "year_clean"], how="left")
    fai = fai.merge(s_total, on=["sector_description", "year_clean"], how="left")
    fai = fai.merge(g_total, on=["year_clean"], how="left")

    # ── Step 3: Compute FAI and Burden Score ──────────────────────────────────
    # country share of sector:  CS / S
    # country share of total:   C  / G
    # FAI = (CS/S) / (C/G)
    fai["country_sector_share"] = fai["cs_funding"] / fai["s_funding"]
    fai["country_total_share"]  = fai["c_funding"]  / fai["g_funding"]

    fai["fai_score"] = np.where(
        (fai["c_funding"] > 0) & (fai["s_funding"] > 0),
        fai["country_sector_share"] / fai["country_total_share"],
        np.nan
    )

    fai["burden_score"] = np.where(
        fai["fai_score"] > 0,
        1.0 / fai["fai_score"],
        np.nan
    )

    fai["fai_score"]    = fai["fai_score"].round(4)
    fai["burden_score"] = fai["burden_score"].round(4)

    # ── Step 4: Add grant count per country-sector-year ───────────────────────
    grant_counts = (
        df_ts.groupby(["country", "sector_description", "year_clean"])
        .size()
        .reset_index(name="grant_count")
    )
    fai = fai.merge(grant_counts, on=["country", "sector_description", "year_clean"], how="left")

    # ── Step 5: Sort and save ─────────────────────────────────────────────────
    fai = fai.sort_values(["year_clean", "country", "sector_description"]).reset_index(drop=True)

    col_order = [
        "year_clean", "country", "country_iso3", "sector_description",
        "cs_funding", "c_funding", "s_funding", "g_funding",
        "country_sector_share", "country_total_share",
        "fai_score", "burden_score", "grant_count",
    ]
    fai = fai[col_order]

    fai.to_csv(OUTPUT_FILE, index=False)

    # ── Summary stats ─────────────────────────────────────────────────────────
    print(f"\n  Output rows: {len(fai):,}  (country x sector x year combinations)")
    print(f"  FAI null (edge cases):  {fai['fai_score'].isna().sum():,}")
    print(f"  FAI <= 0.5 (under-served):  {(fai['fai_score'] <= 0.5).sum():,}")
    print(f"  FAI > 1.0  (over-served):   {(fai['fai_score'] > 1.0).sum():,}")
    print(f"  Median FAI score:  {fai['fai_score'].median():.4f}")
    print(f"  Max burden score:  {fai['burden_score'].max():.2f}  "
          f"({fai.loc[fai['burden_score'].idxmax(), 'country']} / "
          f"{fai.loc[fai['burden_score'].idxmax(), 'sector_description']})")

    print(f"\nSaved -> {OUTPUT_FILE}")
    print("\nTableau load instructions for Tab 4:")
    print("  Load OECD_fai.csv as a separate data source (no join to main needed)")
    print("  Dimensions: year_clean, country, country_iso3, sector_description")
    print("  Metrics:    fai_score, burden_score, cs_funding, grant_count")
    print("  Filter:     exclude nulls in fai_score for the map and dot plot")
    print("  Map role:   use country_iso3 as geographic field")


if __name__ == "__main__":
    main()
