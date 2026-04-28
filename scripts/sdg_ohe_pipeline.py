"""
SDG One-Hot Encoding Pipeline
==============================
OECD Case Competition — Data Preprocessing Script

What this script does:
1. Loads the OECD dataset from Excel
2. For rows WITH sdg_focus: parses semicolon-delimited targets (e.g. "3.1;5.6;15.2"),
   floors each to its integer SDG goal, deduplicates → produces a set like {3, 5, 15}
3. For rows WITHOUT sdg_focus (null): infers the top 1–3 SDGs from subsector_description
   then sector_description using a curated mapping grounded in UN SDG definitions.
   - Specific/targeted subsectors get 1 SDG
   - Broad/multi-theme subsectors get 2–3 SDGs
   - Null rows (unallocated) get all zeros
4. One-hot encodes the result into 17 columns: sdg_goal_1 through sdg_goal_17
5. Saves a cleaned CSV ready for Tableau (original columns + 17 OHE columns appended)

SDG Reference (UN, https://sdgs.un.org/goals):
  1  = No Poverty
  2  = Zero Hunger
  3  = Good Health and Well-Being
  4  = Quality Education
  5  = Gender Equality
  6  = Clean Water and Sanitation
  7  = Affordable and Clean Energy
  8  = Decent Work and Economic Growth
  9  = Industry, Innovation and Infrastructure
  10 = Reduced Inequalities
  11 = Sustainable Cities and Communities
  12 = Responsible Consumption and Production
  13 = Climate Action
  14 = Life Below Water
  15 = Life on Land
  16 = Peace, Justice and Strong Institutions
  17 = Partnerships for the Goals

Author: OECD Case Comp Team
"""

import math
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

INPUT_FILE  = r"c:\Users\WrenzyBoba\Desktop\oecd case comp\OECD Dataset.xlsx"
SHEET_NAME  = "complete_p4d3_df"
OUTPUT_FILE = r"c:\Users\WrenzyBoba\Desktop\oecd case comp\OECD_cleaned_with_SDG_OHE.csv"

# ─────────────────────────────────────────────────────────────────────────────
# SUBSECTOR → SDG MAPPING
# Grounded in OECD CRS codes + UN SDG descriptions (sdgs.un.org/goals)
# Rules:
#   - 1 SDG  → subsector is very targeted to a single goal
#   - 2 SDGs → subsector spans two goals (e.g. reproductive health = health + gender)
#   - 3 SDGs → subsector is genuinely cross-cutting or broad
# ─────────────────────────────────────────────────────────────────────────────

SUBSECTOR_TO_SDG = {
    # ── EDUCATION (110-114) ──────────────────────────────────────────────────
    11110: [4],          # Education policy and administrative management
    11120: [4],          # Education facilities and training
    11130: [4],          # Teacher training
    11182: [4],          # Educational research
    11220: [4],          # Primary education
    11221: [4],          # Sectors not specified (basic ed context)
    11230: [4],          # Basic life skills for adults
    11231: [4],          # Basic life skills for youth
    11232: [4],          # Primary education equivalent for adults
    11233: [4],          # Sectors not specified
    11240: [4],          # Early childhood education
    11250: [2, 4],       # School feeding → hunger + education
    11260: [4],          # Lower secondary education
    11320: [4],          # Upper Secondary Education
    11330: [4, 8],       # Vocational training → education + decent work
    11420: [4],          # Higher education
    11430: [4, 8],       # Advanced technical and managerial training

    # ── HEALTH (120-123) ─────────────────────────────────────────────────────
    12110: [3],          # Health policy and administrative management
    12153: [3],          # Sectors not specified (health context)
    12181: [3],          # Medical education/training
    12182: [3],          # Medical research
    12191: [3],          # Medical services
    12196: [3],          # Health statistics and data
    12220: [3],          # Basic health care
    12230: [3],          # Basic health infrastructure
    12240: [2, 3],       # Basic nutrition → hunger + health
    12241: [3],          # Sectors not specified
    12242: [3],          # Sectors not specified
    12250: [3],          # Infectious disease control
    12261: [3],          # Health education
    12262: [3],          # Malaria control
    12263: [3],          # Tuberculosis control
    12264: [3],          # COVID-19 control
    12281: [3],          # Health personnel development
    12310: [3],          # NCDs control, general
    12320: [3],          # Tobacco use control
    12330: [3],          # Control of harmful use of alcohol and drugs
    12340: [3],          # Promotion of mental health and well-being
    12341: [3],          # Sectors not specified
    12350: [3],          # Other prevention and treatment of NCDs
    12382: [3],          # Research for prevention and control of NCDs
    12664: [3],          # Sectors not specified

    # ── POPULATION / REPRODUCTIVE HEALTH (130) ───────────────────────────────
    13010: [3, 5],       # Population policy and administrative management
    13020: [3, 5],       # Reproductive health care
    13030: [3, 5],       # Family planning
    13040: [3],          # STD control including HIV/AIDS
    13081: [3, 5],       # Personnel development for population and reproductive health
    13096: [3, 5],       # Population statistics and data

    # ── WATER SUPPLY & SANITATION (140) ──────────────────────────────────────
    14010: [6],          # Water sector policy and administrative management
    14015: [6, 15],      # Water resources conservation → water + life on land
    14020: [6],          # Water supply and sanitation - large systems
    14021: [6],          # Water supply - large systems
    14022: [6],          # Sanitation - large systems
    14030: [6],          # Basic drinking water supply and basic sanitation
    14031: [6],          # Basic drinking water supply
    14032: [6],          # Basic sanitation
    14040: [6, 15],      # River basins development → water + ecosystems
    14050: [6, 11],      # Waste management/disposal → water + cities
    14081: [4, 6],       # Education and training in water supply and sanitation
    15010: [6],          # Sectors not specified (water context)

    # ── GOVERNMENT & CIVIL SOCIETY (150-152) ─────────────────────────────────
    15110: [16],         # Public sector policy and administrative management
    15111: [16, 17],     # Public finance management (PFM) → institutions + partnerships
    15112: [16],         # Decentralisation and support to subnational government
    15113: [16],         # Anti-corruption organisations and institutions
    15114: [17],         # Domestic revenue mobilisation
    15125: [16],         # Public Procurement
    15126: [16],         # Other general public services
    15127: [16, 17],     # National monitoring and evaluation
    15128: [16],         # Local government finance
    15129: [16],         # Other central transfers to institutions
    15130: [16],         # Legal and judicial development
    15131: [16],         # Justice, law and order policy
    15132: [16],         # Police
    15133: [16],         # Fire and rescue services
    15136: [10, 16],     # Immigration → inequality + institutions
    15142: [8, 17],      # Macroeconomic policy → growth + partnerships
    15144: [9, 16],      # National standards development
    15150: [16],         # Democratic participation and civil society
    15151: [16],         # Elections
    15152: [16],         # Legislatures and political parties
    15153: [16],         # Media and free flow of information
    15160: [10, 16],     # Human rights → inequality + peace/justice
    15170: [5, 16],      # Women's rights organisations → gender + institutions
    15180: [5, 16],      # Ending violence against women and girls
    15181: [5, 16],      # Sectors not specified (women's context)
    15183: [16],         # Sectors not specified
    15184: [16],         # Sectors not specified
    15185: [16],         # Local government administration
    15190: [10, 16],     # Facilitation of orderly migration and mobility
    15210: [16],         # Security system management and reform
    15220: [16],         # Civilian peace-building, conflict prevention and resolution

    # ── OTHER SOCIAL INFRASTRUCTURE & SERVICES (160) ─────────────────────────
    # This sector is broad — typically gets 2–3 SDGs
    16010: [1, 10],      # Social/welfare services → poverty + inequality
    16020: [8],          # Employment policy and administrative management
    16050: [11],         # Housing policy and administrative management
    16062: [17],         # Statistical capacity building
    16063: [17],         # Narcotics control
    16064: [16],         # Social mitigation of HIV/AIDS
    16065: [1, 10],      # Reconstruction relief
    16066: [10],         # Culture and recreation

    # ── TRANSPORT & STORAGE (210) ─────────────────────────────────────────────
    21010: [9, 11],      # Transport policy and administrative management
    21020: [9, 11],      # Road transport
    21030: [9],          # Rail transport
    21040: [9],          # Water transport
    21050: [9],          # Air transport
    21061: [9],          # Storage
    21081: [9],          # Education/training in transport and storage

    # ── COMMUNICATIONS (220) ─────────────────────────────────────────────────
    22010: [9],          # Communications policy and administrative management
    22020: [9],          # Telecommunications
    22030: [9],          # Radio/television/print media
    22040: [9],          # Information and communication technology (ICT)

    # ── ENERGY (230) ─────────────────────────────────────────────────────────
    23010: [7],          # Energy policy and administrative management
    23020: [7, 13],      # Energy generation (renewable sources) → energy + climate
    23030: [7],          # Energy generation (non-renewable)
    23040: [7],          # Hybrid energy electric power plants
    23050: [7],          # Nuclear energy plants
    23061: [7],          # Fuelwood/charcoal (energy)
    23067: [7],          # Biofuel production
    23110: [7],          # Energy distribution
    23181: [7, 4],       # Education and training in energy
    23182: [7, 9],       # Energy research

    # ── BANKING & FINANCIAL SERVICES (240) ───────────────────────────────────
    24010: [8, 10],      # Financial policy and administrative management
    24020: [8],          # Formal sector financial intermediaries
    24030: [8],          # Informal/semi-formal financial intermediaries
    24040: [8, 1],       # Micro-finance → decent work + poverty
    24050: [8],          # Remittance facilitation, promotion and optimisation
    24081: [8],          # Education/training in banking and financial services

    # ── BUSINESS & OTHER SERVICES (250) ──────────────────────────────────────
    25010: [8],          # Business support services and institutions
    25020: [8],          # Privatisation
    25030: [8],          # Audiovisual services
    25040: [8],          # Facilitation of regional integration

    # ── AGRICULTURE, FORESTRY, FISHING (310) ─────────────────────────────────
    31110: [2],          # Agricultural policy and administrative management
    31120: [2],          # Agricultural development
    31130: [2],          # Agricultural land resources
    31140: [2],          # Agricultural water resources
    31150: [2, 15],      # Agricultural inputs
    31161: [2],          # Food crop production
    31162: [2, 8],       # Industrial crops/export crops
    31163: [2],          # Livestock
    31164: [2, 1],       # Agrarian reform → hunger + poverty
    31165: [2, 8],       # Agricultural alternative development
    31166: [2],          # Agricultural extension
    31181: [2, 4],       # Agricultural education/training
    31182: [2, 9],       # Agricultural research
    31191: [2],          # Agricultural services
    31192: [2, 15],      # Plant and post-harvest protection and pest control
    31193: [8],          # Agricultural financial services
    31194: [8],          # Agricultural co-operatives
    31195: [2],          # Livestock/veterinary services
    31210: [15],         # Forestry policy and administrative management
    31220: [15],         # Forestry development
    31261: [7, 15],      # Fuelwood/charcoal (forestry) → energy + land
    31281: [4, 15],      # Forestry education/training
    31282: [15, 9],      # Forestry research
    31291: [15],         # Forestry services
    31310: [14],         # Fishing policy and administrative management
    31320: [14],         # Fishery development
    31330: [14],         # Sectors not specified (fishery context)
    31381: [4, 14],      # Fishery education/training
    31382: [14, 9],      # Fishery research
    31391: [14],         # Fishery services

    # ── INDUSTRY, MINING, CONSTRUCTION (320) ─────────────────────────────────
    32110: [9],          # Industrial policy and administrative management
    32120: [9],          # Industrial development
    32130: [8, 9],       # Small and medium-sized enterprises (SME) development
    32140: [8],          # Cottage industries and handicraft
    32161: [2, 9],       # Agro-industries
    32162: [15, 9],      # Forest industries
    32163: [9],          # Textiles, leather and substitutes
    32165: [2, 9],       # Fertilizer plants
    32166: [9],          # Cement/lime/plaster
    32167: [7, 13],      # Energy manufacturing (fossil fuels) → energy + climate
    32168: [3, 9],       # Pharmaceutical production
    32169: [9],          # Basic metal industries
    32171: [9],          # Engineering
    32172: [9],          # Transport equipment industry
    32174: [7, 13],      # Clean cooking appliances manufacturing
    32182: [9],          # Technological research and development
    32210: [9],          # Mineral/mining policy and administrative management
    32220: [9],          # Mineral prospection and exploration
    32261: [7, 13],      # Coal
    32262: [7, 13],      # Oil and gas (upstream)
    32263: [9],          # Ferrous metals
    32264: [9],          # Nonferrous metals
    32265: [9],          # Precious metals/materials
    32310: [9, 11],      # Construction policy and administrative management
    32311: [9],          # Sectors not specified (construction)

    # ── TRADE POLICIES & REGULATIONS (330) ───────────────────────────────────
    33110: [8, 17],      # Trade policy and administrative management
    33120: [8, 17],      # Trade facilitation
    33130: [17],         # Regional trade agreements (RTAs)
    33140: [17],         # Multilateral trade negotiations
    33181: [8, 4],       # Trade education/training
    33210: [8],          # Tourism policy and administrative management

    # ── GENERAL ENVIRONMENT PROTECTION (410) ─────────────────────────────────
    41010: [13, 15],     # Environmental policy and administrative management
    41020: [15],         # Biosphere protection
    41030: [15],         # Biodiversity
    41040: [15],         # Site preservation
    41050: [13, 15],     # Sectors not specified (environment context)
    41081: [4, 13],      # Environmental education/training
    41082: [13, 15],     # Environmental research

    # ── OTHER MULTISECTOR (430) ───────────────────────────────────────────────
    43010: [1, 10, 17],  # Multisector aid → poverty + inequality + partnerships (broad)
    43030: [11],         # Urban development and management
    43032: [11],         # Urban development
    43040: [1, 2],       # Rural development → poverty + hunger
    43042: [1, 2],       # Rural development (alt code)
    43050: [1, 8],       # Non-agricultural alternative development
    43060: [11, 13],     # Disaster Risk Reduction → cities + climate
    43071: [2, 17],      # Food security policy and administrative management
    43072: [2],          # Household food security programmes
    43073: [2, 12],      # Food safety and quality → hunger + consumption
    43081: [4, 17],      # Multisector education/training
    43082: [9, 17],      # Research/scientific institutions

    # ── BUDGET SUPPORT / COMMODITIES / DEBT (510-600) ────────────────────────
    51010: [17],         # General budget support-related aid
    52010: [2],          # Food assistance
    52020: [2],          # Sectors not specified (food assistance context)
    53040: [17],         # Import support (commodities)
    60010: [17],         # Action relating to debt
    60030: [17],         # Relief of multilateral debt
    60061: [17],         # Debt for development swap

    # ── EMERGENCY RESPONSE (720) ──────────────────────────────────────────────
    72010: [1],          # Material relief assistance and services
    72011: [3],          # Basic Health Care Services in Emergencies
    72012: [4],          # Education in emergencies
    72040: [2],          # Emergency food assistance
    72050: [17],         # Relief co-ordination and support services

    # ── RECONSTRUCTION / DISASTER (730-740) ──────────────────────────────────
    73010: [11],         # Immediate post-emergency reconstruction and rehabilitation
    74020: [11, 13],     # Multi-hazard response preparedness

    # ── ADMIN / REFUGEES / UNSPECIFIED (910-998) ─────────────────────────────
    91010: [17],         # Administrative costs (non-sector allocable)
    91011: [17],         # Sectors not specified
    93010: [10, 16],     # Refugees/asylum seekers in donor countries
    93012: [4, 10],      # Refugees in donor countries - training
    93013: [3, 10],      # Refugees in donor countries - health
    93014: [1, 10],      # Refugees in donor countries - other temporary sustenance
    99810: [],           # Sectors not specified (unallocated) → no SDG
    99820: [17],         # Promotion of development awareness
}

# Sector-level fallback (when subsector not matched or missing)
SECTOR_TO_SDG = {
    110: [4],            # Education
    111: [4],
    112: [4],
    113: [4],
    114: [4],
    120: [3],            # Health
    121: [3],
    122: [3],
    123: [3],
    130: [3, 5],         # Population/Reproductive Health
    140: [6],            # Water Supply & Sanitation
    150: [16],           # Government & Civil Society
    151: [16],
    152: [16],
    160: [1, 10],        # Other Social Infrastructure (broad)
    210: [9, 11],        # Transport & Storage
    220: [9],            # Communications
    230: [7],            # Energy
    240: [8, 10],        # Banking & Financial Services
    250: [8],            # Business & Other Services
    310: [2, 15],        # Agriculture, Forestry, Fishing (broad)
    320: [9],            # Industry, Mining, Construction
    321: [9],
    322: [9],
    323: [9],
    330: [8, 17],        # Trade Policies & Regulations
    331: [8, 17],
    332: [17],
    410: [13, 15],       # General Environment Protection
    430: [1, 10, 17],    # Other Multisector (broad)
    510: [17],           # General Budget Support
    520: [2],            # Development Food Assistance
    530: [17],           # Other Commodity Assistance
    600: [17],           # Action Relating to Debt
    720: [1, 13],        # Emergency Response
    730: [11],           # Reconstruction Relief & Rehabilitation
    740: [11, 13],       # Disaster Prevention & Preparedness
    910: [17],           # Administrative Costs of Donors
    930: [10, 16],       # Refugees in Donor Countries
    998: [],             # Unallocated / Unspecified → no SDG inferred
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def parse_existing_sdg(sdg_str):
    """
    Parse a semicolon-delimited sdg_focus string into a set of integer SDG goals.
    E.g. "3.1;5.6;15.2" → {3, 5, 15}
    Floors each target to its integer parent goal.
    """
    if pd.isna(sdg_str) or str(sdg_str).strip() == "":
        return set()
    goals = set()
    for token in str(sdg_str).split(";"):
        token = token.strip()
        if not token:
            continue
        try:
            # Floor to integer (e.g. 15.9 → 15)
            goal = int(math.floor(float(token)))
            if 1 <= goal <= 17:
                goals.add(goal)
        except ValueError:
            pass  # skip malformed tokens
    return goals


def infer_sdg_from_sector(subsector_val, sector_val):
    """
    Infer SDG goals from subsector code (preferred) or sector code (fallback).
    Returns a set of integer SDG goal numbers.
    Returns empty set if nothing can be inferred (unallocated, NaN).
    """
    # Try subsector first (more targeted)
    try:
        sub_key = int(float(subsector_val))
        if sub_key in SUBSECTOR_TO_SDG:
            return set(SUBSECTOR_TO_SDG[sub_key])
    except (ValueError, TypeError):
        pass

    # Fall back to broad sector
    try:
        sec_key = int(float(sector_val))
        if sec_key in SECTOR_TO_SDG:
            return set(SECTOR_TO_SDG[sec_key])
    except (ValueError, TypeError):
        pass

    return set()


def goals_to_ohe(goals):
    """Convert a set of SDG goal integers to a dict of 17 OHE columns."""
    return {f"sdg_goal_{i}": (1 if i in goals else 0) for i in range(1, 18)}


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("Loading dataset...")
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")

    total = len(df)
    has_sdg   = df["sdg_focus"].notna().sum()
    no_sdg    = df["sdg_focus"].isna().sum()
    print(f"  Rows with sdg_focus:    {has_sdg:,} ({has_sdg/total*100:.1f}%)")
    print(f"  Rows without sdg_focus: {no_sdg:,} ({no_sdg/total*100:.1f}%)")

    print("\nProcessing SDG goals...")
    sdg_goal_sets = []

    for _, row in df.iterrows():
        if pd.notna(row["sdg_focus"]) and str(row["sdg_focus"]).strip():
            # Route 1: parse from existing sdg_focus
            goals = parse_existing_sdg(row["sdg_focus"])
        else:
            # Route 2: infer from subsector → sector
            goals = infer_sdg_from_sector(row.get("subsector"), row.get("Sector"))

        sdg_goal_sets.append(goals)

    # Build OHE columns
    ohe_rows = [goals_to_ohe(g) for g in sdg_goal_sets]
    ohe_df   = pd.DataFrame(ohe_rows)

    # Attach OHE columns to original dataframe
    df_out = pd.concat([df.reset_index(drop=True), ohe_df], axis=1)

    # ── Summary stats ────────────────────────────────────────────────────────
    inferred_mask = df["sdg_focus"].isna()
    inferred_non_zero = sum(
        any(v == 1 for v in r.values())
        for r, flag in zip(ohe_rows, inferred_mask)
        if flag
    )
    still_zero = no_sdg - inferred_non_zero

    print(f"\n--- SDG Assignment Summary ---")
    print(f"  Parsed from existing sdg_focus:  {has_sdg:,} rows")
    print(f"  Inferred from sector/subsector:  {inferred_non_zero:,} rows")
    print(f"  No SDG assignable (all zeros):   {still_zero:,} rows (Unallocated/Admin)")
    print(f"  Total coverage:                  {has_sdg + inferred_non_zero:,} / {total:,} rows")

    print(f"\n--- SDG Goal Distribution (across all rows) ---")
    for i in range(1, 18):
        col = f"sdg_goal_{i}"
        count = ohe_df[col].sum()
        print(f"  SDG {i:2d}: {count:6,} rows  ({count/total*100:4.1f}%)")

    print(f"\nSaving to {OUTPUT_FILE} ...")
    df_out.to_csv(OUTPUT_FILE, index=False)
    print(f"  Done! Saved {len(df_out):,} rows x {len(df_out.columns)} columns.")
    print(f"\n  New columns added: sdg_goal_1 through sdg_goal_17")
    print(f"  Original sdg_focus column preserved for reference.")


if __name__ == "__main__":
    main()
