"""
Final Enhancements — ISO Codes, Thematic Score, Commitment Gap, Timeline Events
================================================================================
OECD Case Competition — Data Preprocessing Script

Prerequisite: Run tableau_prep.py first to generate OECD_main.csv

What this script produces (all in the project root folder):
  1. OECD_main.csv         — UPDATED with 3 new columns:
                               country_iso3     (ISO 3166-1 alpha-3 code for Tableau maps)
                               thematic_score   (0.0-1.0, null if grant was never screened)
                               commitment_gap   (usd_commitment_defl - usd_disbursements_defl)
  2. OECD_timeline.csv     — 5-row events table for Tab 1 time series annotations

Transparency notes logged to console:
  - Which country names had no ISO match (regional / multi-country / unspecified)
  - Thematic score coverage
  - Commitment gap coverage

Author: OECD Case Comp Team
"""

import sys
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MAIN_FILE     = r"c:\Users\WrenzyBoba\Desktop\oecd case comp\OECD_main.csv"
TIMELINE_FILE = r"c:\Users\WrenzyBoba\Desktop\oecd case comp\OECD_timeline.csv"

# ─────────────────────────────────────────────────────────────────────────────
# ISO 3166-1 ALPHA-3 MAPPING
# Covers every true country name in the dataset.
# Regional entries, multi-country strings, and unspecified rows map to None
# (Tableau will simply leave them unplotted on the map, which is correct).
# Encoding note: the CSV is UTF-8 so accented chars should round-trip fine.
# ─────────────────────────────────────────────────────────────────────────────

COUNTRY_TO_ISO3 = {
    "Afghanistan":                              "AFG",
    "Albania":                                  "ALB",
    "Algeria":                                  "DZA",
    "Angola":                                   "AGO",
    "Argentina":                                "ARG",
    "Armenia":                                  "ARM",
    "Azerbaijan":                               "AZE",
    "Bangladesh":                               "BGD",
    "Belarus":                                  "BLR",
    "Belize":                                   "BLZ",
    "Benin":                                    "BEN",
    "Bhutan":                                   "BTN",
    "Bolivia":                                  "BOL",
    "Bosnia and Herzegovina":                   "BIH",
    "Botswana":                                 "BWA",
    "Brazil":                                   "BRA",
    "Burkina Faso":                             "BFA",
    "Burundi":                                  "BDI",
    "Cabo Verde":                               "CPV",
    "Cambodia":                                 "KHM",
    "Cameroon":                                 "CMR",
    "Central African Republic":                 "CAF",
    "Chad":                                     "TCD",
    "China (People's Republic of)":             "CHN",
    "Colombia":                                 "COL",
    "Comoros":                                  "COM",
    "Congo":                                    "COG",
    "Costa Rica":                               "CRI",
    "Cuba":                                     "CUB",
    "Côte d'Ivoire":                            "CIV",
    "C\u00f4te d'Ivoire":                       "CIV",   # UTF-8 form
    "C?te d'Ivoire":                            "CIV",   # garbled fallback
    "Democratic People's Republic of Korea":    "PRK",
    "Democratic Republic of the Congo":         "COD",
    "Djibouti":                                 "DJI",
    "Dominica":                                 "DMA",
    "Dominican Republic":                       "DOM",
    "Ecuador":                                  "ECU",
    "Egypt":                                    "EGY",
    "El Salvador":                              "SLV",
    "Equatorial Guinea":                        "GNQ",
    "Eritrea":                                  "ERI",
    "Eswatini":                                 "SWZ",
    "Ethiopia":                                 "ETH",
    "Fiji":                                     "FJI",
    "Gabon":                                    "GAB",
    "Gambia":                                   "GMB",
    "Georgia":                                  "GEO",
    "Ghana":                                    "GHA",
    "Grenada":                                  "GRD",
    "Guatemala":                                "GTM",
    "Guinea":                                   "GIN",
    "Guinea-Bissau":                            "GNB",
    "Guyana":                                   "GUY",
    "Haiti":                                    "HTI",
    "Honduras":                                 "HND",
    "India":                                    "IND",
    "Indonesia":                                "IDN",
    "Iran":                                     "IRN",
    "Iraq":                                     "IRQ",
    "Jamaica":                                  "JAM",
    "Jordan":                                   "JOR",
    "Kazakhstan":                               "KAZ",
    "Kenya":                                    "KEN",
    "Kiribati":                                 "KIR",
    "Kosovo":                                   "XKX",   # Kosovo (not in ISO but XKX is the de facto code)
    "Kyrgyzstan":                               "KGZ",
    "Lao People's Democratic Republic":         "LAO",
    "Lebanon":                                  "LBN",
    "Lesotho":                                  "LSO",
    "Liberia":                                  "LBR",
    "Libya":                                    "LBY",
    "Madagascar":                               "MDG",
    "Malawi":                                   "MWI",
    "Malaysia":                                 "MYS",
    "Maldives":                                 "MDV",
    "Mali":                                     "MLI",
    "Marshall Islands":                         "MHL",
    "Mauritania":                               "MRT",
    "Mauritius":                                "MUS",
    "Mexico":                                   "MEX",
    "Micronesia":                               "FSM",
    "Moldova":                                  "MDA",
    "Mongolia":                                 "MNG",
    "Montenegro":                               "MNE",
    "Montserrat":                               "MSR",
    "Morocco":                                  "MAR",
    "Mozambique":                               "MOZ",
    "Myanmar":                                  "MMR",
    "Namibia":                                  "NAM",
    "Nepal":                                    "NPL",
    "Nicaragua":                                "NIC",
    "Niger":                                    "NER",
    "Nigeria":                                  "NGA",
    "North Macedonia":                          "MKD",
    "Pakistan":                                 "PAK",
    "Palau":                                    "PLW",
    "Panama":                                   "PAN",
    "Papua New Guinea":                         "PNG",
    "Paraguay":                                 "PRY",
    "Peru":                                     "PER",
    "Philippines":                              "PHL",
    "Rwanda":                                   "RWA",
    "Saint Helena":                             "SHN",
    "Saint Lucia":                              "LCA",
    "Saint Vincent and the Grenadines":         "VCT",
    "Samoa":                                    "WSM",
    "Senegal":                                  "SEN",
    "Serbia":                                   "SRB",
    "Sierra Leone":                             "SLE",
    "Solomon Islands":                          "SLB",
    "Somalia":                                  "SOM",
    "South Africa":                             "ZAF",
    "South Sudan":                              "SSD",
    "Sri Lanka":                                "LKA",
    "Sudan":                                    "SDN",
    "Suriname":                                 "SUR",
    "Syrian Arab Republic":                     "SYR",
    "São Tomé and Príncipe":                    "STP",
    "S\u00e3o Tom\u00e9 and Pr\u00edncipe":     "STP",
    "S?o Tom? and Pr?ncipe":                    "STP",   # garbled fallback
    "Tajikistan":                               "TJK",
    "Tanzania":                                 "TZA",
    "Thailand":                                 "THA",
    "Timor-Leste":                              "TLS",
    "Togo":                                     "TGO",
    "Tonga":                                    "TON",
    "Tunisia":                                  "TUN",
    "Turkmenistan":                             "TKM",
    "Türkiye":                                  "TUR",
    "T\u00fcrkiye":                             "TUR",   # UTF-8 form
    "T?rkiye":                                  "TUR",   # garbled fallback
    "Uganda":                                   "UGA",
    "Ukraine":                                  "UKR",
    "Uzbekistan":                               "UZB",
    "Vanuatu":                                  "VUT",
    "Venezuela":                                "VEN",
    "Viet Nam":                                 "VNM",
    "West Bank and Gaza Strip":                 "PSE",
    "Yemen":                                    "YEM",
    "Zambia":                                   "ZMB",
    "Zimbabwe":                                 "ZWE",
    # ── Regional / unspecified → None (intentionally not mapped) ─────────────
    # These are legitimately regional entries; leaving them null in country_iso3
    # tells Tableau not to plot them as individual countries on the map.
    # They will still show up in region_macro / region drill-downs.
    "Africa, regional":                         None,
    "America, regional":                        None,
    "Asia, regional":                           None,
    "Caribbean & Central America, regional":    None,
    "Caribbean, regional":                      None,
    "Central America, regional":                None,
    "Central Asia, regional":                   None,
    "Eastern Africa, regional":                 None,
    "Europe, regional":                         None,
    "Far East Asia, regional":                  None,
    "GLOBAL or unspecified":                    None,
    "Developing countries, unspecified":        None,
    "Bilateral, unspecified":                   None,
    "Middle Africa, regional":                  None,
    "Middle East, regional":                    None,
    "Micronesia, regional":                     None,
    "North of Sahara, regional":                None,
    "Oceania, regional":                        None,
    "South & Central Asia, regional":           None,
    "South America, regional":                  None,
    "South Asia, regional":                     None,
    "South of Sahara, regional":                None,
    "Southern Africa, regional":                None,
    "States Ex-Yugoslavia unspecified":         None,
    "Western Africa, regional":                 None,
}

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
MAX_THEMATIC = 2.0 * len(THEMATIC_MARKERS)  # = 14.0 (max possible raw score)


def compute_thematic_score(row):
    """
    Returns a 0.0-1.0 normalized thematic score for a grant row.
    Logic:
      - Only score the markers that are NOT null (i.e., were actually screened).
      - If NONE of the 7 markers were screened → return None (null).
        This preserves the "unscreened" status distinct from "screened, scored 0."
      - Otherwise: sum the screened marker values / (2 * number_screened)
        so the score is relative to what was actually assessed.
    Rationale: a grant screened on 3 markers and scoring 2+2+2 should get 1.0,
    not penalized for the 4 markers that were out of scope for that funder.
    """
    screened_vals = []
    for col in THEMATIC_MARKERS:
        v = row.get(col)
        if v is not None and not (isinstance(v, float) and pd.isna(v)):
            screened_vals.append(float(v))

    if not screened_vals:
        return None  # never screened → null, not zero

    max_possible = 2.0 * len(screened_vals)
    return round(sum(screened_vals) / max_possible, 4)


def main():
    print("Loading OECD_main.csv ...")
    df = pd.read_csv(MAIN_FILE, low_memory=False)
    print(f"  {len(df):,} rows x {len(df.columns)} columns")

    # ── 1. ISO country codes ──────────────────────────────────────────────────
    print("\n[1/3] Adding country_iso3 ...")

    df["country_iso3"] = df["country"].map(lambda x: COUNTRY_TO_ISO3.get(str(x).strip()) if pd.notna(x) else None)

    mapped     = df["country_iso3"].notna().sum()
    null_count = df["country_iso3"].isna().sum()
    print(f"  Mapped to ISO3:   {mapped:,} rows ({mapped/len(df)*100:.1f}%)")
    print(f"  Left null (regional/multi/unspecified): {null_count:,} rows ({null_count/len(df)*100:.1f}%)")

    # Report any country names that didn't match anything in our dict
    all_countries = df["country"].dropna().unique()
    unmatched = []
    for c in sorted(all_countries):
        c_str = str(c).strip()
        # Multi-country strings contain semicolons — skip intentionally
        if ";" in c_str:
            continue
        if c_str not in COUNTRY_TO_ISO3:
            unmatched.append(c_str)

    if unmatched:
        print(f"\n  WARNING: {len(unmatched)} country name(s) not in mapping (left null):")
        for u in unmatched:
            print(f"    '{u}'")
    else:
        print("  All single-country names successfully mapped.")

    # ── 2. Thematic score ─────────────────────────────────────────────────────
    print("\n[2/3] Computing thematic_score ...")

    # Cast marker columns to numeric safely
    for col in THEMATIC_MARKERS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["thematic_score"] = df.apply(compute_thematic_score, axis=1)

    n_scored  = df["thematic_score"].notna().sum()
    n_null    = df["thematic_score"].isna().sum()
    n_zero    = (df["thematic_score"] == 0.0).sum()
    n_perfect = (df["thematic_score"] == 1.0).sum()
    avg_score = df["thematic_score"].mean()

    print(f"  Grants with thematic_score:  {n_scored:,} ({n_scored/len(df)*100:.1f}%)")
    print(f"  Grants with null score:      {n_null:,} ({n_null/len(df)*100:.1f}%) [unscreened]")
    print(f"  Score = 0.0 (none targeted): {n_zero:,}")
    print(f"  Score = 1.0 (all principal): {n_perfect:,}")
    print(f"  Mean score (screened only):  {avg_score:.4f}")

    # ── 3. Commitment gap ─────────────────────────────────────────────────────
    print("\n[3/3] Computing commitment_gap ...")

    df["usd_commitment_defl"] = pd.to_numeric(df["usd_commitment_defl"], errors="coerce")
    df["usd_disbursements_defl"] = pd.to_numeric(df["usd_disbursements_defl"], errors="coerce")
    df["commitment_gap"] = df["usd_commitment_defl"] - df["usd_disbursements_defl"]

    n_gap     = df["commitment_gap"].notna().sum()
    pos_gap   = (df["commitment_gap"] > 0).sum()   # promised > paid (under-delivered)
    neg_gap   = (df["commitment_gap"] < 0).sum()   # paid > promised (over-delivered)
    zero_gap  = (df["commitment_gap"] == 0).sum()  # exact match

    print(f"  Rows with commitment_gap:    {n_gap:,} ({n_gap/len(df)*100:.1f}%)")
    print(f"  Under-delivered (gap > 0):   {pos_gap:,}  (committed more than paid)")
    print(f"  Over-delivered  (gap < 0):   {neg_gap:,}  (paid more than committed)")
    print(f"  Exact match     (gap = 0):   {zero_gap:,}")

    # ── Save updated main CSV ─────────────────────────────────────────────────
    print(f"\nSaving updated OECD_main.csv ...")
    df.to_csv(MAIN_FILE, index=False)
    print(f"  Saved {len(df):,} rows x {len(df.columns)} columns")
    print(f"  New columns: country_iso3, thematic_score, commitment_gap")

    # ── 4. Timeline events CSV ────────────────────────────────────────────────
    print(f"\n[4/4] Creating OECD_timeline.csv ...")

    timeline = pd.DataFrame([
        {"year": 2015, "event_label": "Paris Agreement",           "event_category": "Climate"},
        {"year": 2017, "event_label": "SDGs Enter Force",          "event_category": "Global Policy"},
        {"year": 2020, "event_label": "COVID-19 Pandemic",         "event_category": "Health"},
        {"year": 2021, "event_label": "COP26 Glasgow",             "event_category": "Climate"},
        {"year": 2022, "event_label": "Russia-Ukraine War",        "event_category": "Humanitarian"},
        {"year": 2023, "event_label": "SDG Midpoint Review",       "event_category": "Global Policy"},
    ])

    timeline.to_csv(TIMELINE_FILE, index=False)
    print(f"  Saved {len(timeline)} events to OECD_timeline.csv")
    print(timeline.to_string(index=False))

    # ── Final summary ─────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("DONE. All files updated:")
    print(f"  OECD_main.csv     -> {len(df):,} rows x {len(df.columns)} cols")
    print(f"  OECD_timeline.csv -> {len(timeline)} rows")
    print("\nTableau notes:")
    print("  - Use country_iso3 as geographic role for the choropleth map")
    print("  - thematic_score: null = unscreened (use as filter), 0-1 = scored")
    print("  - commitment_gap: positive = under-delivered, negative = over-delivered")
    print("  - Load OECD_timeline.csv, join on year for reference line annotations")
    print("="*60)


if __name__ == "__main__":
    main()
