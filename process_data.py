"""
Wyscout data processing pipeline for the Eredivisie (2022/23 - 2025/26).
Replicates the logic of scouting_general.py (loading, minutes filter, FotMob
possession, position normalization, PAdj/OPAdj adjustment and per-pillar
percentiles) for a single-league dataset spanning several seasons.
"""
import json
import os
import re

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
POSSESSION_PATH = os.path.join(BASE_DIR, "data", "fotmob_possession.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "processed.parquet")

MIN_MINUTES = 900
PERIOD_COL = "Equipo durante el período seleccionado"

FILES = [
    ("DEF_MID_GK 2526.xlsx", "25/26"),
    ("ATT 2526.xlsx", "25/26"),
    ("DEF_MID_GK 2425.xlsx", "24/25"),
    ("ATT 2425.xlsx", "24/25"),
    ("DEF_MID_GK 2324.xlsx", "23/24"),
    ("ATT 2324.xlsx", "23/24"),
    ("DEF_MID_GK 2223.xlsx", "22/23"),
    ("ATT 2223.xlsx", "22/23"),
]

SEASON_TO_POSSESSION_KEY = {
    "25/26": "2526",
    "24/25": "2425",
    "23/24": "2324",
    "22/23": "2223",
}

# ==========================================
# 1. LOAD FILES AND FILTER BY MINUTES
# ==========================================
def cargar_todo():
    frames = []
    for fname, temporada in FILES:
        path = os.path.join(RAW_DIR, fname)
        if not os.path.exists(path):
            print(f"WARNING: not found {path}")
            continue
        df = pd.read_excel(path)
        df["Temporada"] = temporada
        df["Liga"] = "Eredivisie"
        if "Minutos jugados" in df.columns:
            df = df[df["Minutos jugados"] >= MIN_MINUTES].copy()
        frames.append(df)
        print(f"  Loaded {fname}: {len(df)} players with >= {MIN_MINUTES} min")
    return pd.concat(frames, ignore_index=True)


# ==========================================
# 2. POSSESSION (FotMob) PER TEAM AND SEASON
# ==========================================
def aplicar_posesion(df):
    with open(POSSESSION_PATH, "r", encoding="utf-8") as f:
        possession_by_season = json.load(f)

    df = df.copy()
    if PERIOD_COL in df.columns:
        df["Equipo"] = df[PERIOD_COL].fillna(df["Equipo"])

    def lookup(row):
        key = SEASON_TO_POSSESSION_KEY.get(row["Temporada"])
        mapa = possession_by_season.get(key, {})
        return mapa.get(row["Equipo"])

    df["team_possession"] = df.apply(lookup, axis=1)

    before = len(df)
    df = df.dropna(subset=["team_possession"]).copy()
    removed = before - len(df)
    print(f"Possession applied. Removed {removed} player(s) whose team wasn't in the "
          f"possession map (reserve/B teams, loans outside the Eredivisie, etc.)")
    return df


# ==========================================
# 3. POSITION NORMALIZATION
# ==========================================
MAPEO_GRUPOS = {
    "RCMF": "CMF", "LCMF": "CMF",
    "RAMF": "RW", "LAMF": "LW",
    "LWF": "LW",
    "RWF": "RW",
    "LDMF": "DMF", "RDMF": "DMF",
    "RWB": "RB", "LWB": "LB",
    "LCB": "CB", "RCB": "CB",
}


def limpieza_posiciones(df):
    df = df.copy()
    df["Posición específica"] = df["Posición específica"].str.strip()
    df["Posición_Principal"] = df["Posición específica"].str.split(",").str[0].str.strip()
    df["Pos_Normalizada"] = df["Posición_Principal"].map(MAPEO_GRUPOS).fillna(df["Posición_Principal"])
    return df


# ==========================================
# 4. METRIC / PILLAR CONFIGURATION PER POSITION
# ==========================================
_SHARED = {
    "defensivas": ["Interceptaciones/90", "Entradas/90", "Duelos defensivos/90",
                   "Faltas/90", "Duelos aéreos en los 90"],
    "ofensivas": ["Pases progresivos/90", "Carreras en progresión/90",
                  "Pases largos/90", "Centros/90",
                  "Regates/90", "xA/90", "Desmarques/90", "xG/90"],
    "pilares": {
        "Aggression": ["Faltas/90_PAdj", "Entradas/90_PAdj"],
        "Defensive Duels": ["Duelos defensivos ganados, %", "Duelos defensivos/90_PAdj"],
        "Interceptions": ["Interceptaciones/90_PAdj"],
        "Progressive Passes": ["Pases progresivos/90_OPAdj", "Precisión pases progresivos, %"],
        "Long Passes": ["Pases largos/90_OPAdj", "Precisión pases largos, %"],
        "Ball Carrying": ["Carreras en progresión/90_OPAdj"],
        "Dribbling": ["Regates/90_OPAdj", "Regates realizados, %"],
        "Crossing": ["Crossing/90_OPAdj", "Precisión centros, %"],
        "Creativity": ["xA/90_OPAdj"],
        "Off-ball Runs": ["Desmarques/90_OPAdj", "Precisión desmarques, %"],
        "Goal Threat": ["xG/90_OPAdj"],
        "Aerial Duels": ["Duelos aéreos en los 90_PAdj", "Duelos aéreos ganados, %"],
    },
}

_GK = {
    "defensivas": ["Goles evitados/90", "Salidas/90"],
    "ofensivas": ["Pases progresivos/90", "Pases largos/90"],
    "pilares": {
        "Shot Stopping": ["Goles evitados/90"],
        "Sweeping": ["Salidas/90_PAdj"],
        "Long Passes": ["Pases largos/90_OPAdj", "Precisión pases largos, %"],
        "Progressive Passes": ["Pases progresivos/90_OPAdj", "Precisión pases progresivos, %"],
    },
}

CONFIG_POSICIONES = {
    "CB": _SHARED, "RB": _SHARED, "LB": _SHARED, "DMF": _SHARED, "CMF": _SHARED,
    "AMF": _SHARED, "LW": _SHARED, "RW": _SHARED, "CF": _SHARED, "GK": _GK,
}


# ==========================================
# 5. POSSESSION ADJUSTMENT (PAdj / OPAdj) AND PER-PILLAR RATINGS
# ==========================================
def rankings(df):
    df = df.copy()
    all_results = []

    for target_pos, conf in CONFIG_POSICIONES.items():
        df_pos = df[df["Pos_Normalizada"] == target_pos].copy()
        if df_pos.empty:
            continue

        if target_pos == "GK" and "Goles evitados/90" in df_pos.columns:
            df_pos["Goles evitados/90"] = -df_pos["Goles evitados/90"]

        for stat in conf["defensivas"]:
            if stat in df_pos.columns:
                df_pos[f"{stat}_PAdj"] = df_pos[stat] * (50 / (100 - df_pos["team_possession"]))

        for stat in conf["ofensivas"]:
            if stat in df_pos.columns:
                df_pos[f"{stat}_OPAdj"] = df_pos[stat] * (50 / df_pos["team_possession"])

        # NOTE: the "Crossing" pillar references "Crossing/90_OPAdj", which is never
        # generated (only "Centros/90_OPAdj" is, from the Spanish source column name).
        # This faithfully reproduces the original pipeline's behavior
        # (scouting_general.py) -> in practice "Crossing" only uses
        # "Precisión centros, %". Left uncorrected on purpose.

        # --- RATING PER SEASON (equivalent to the original pipeline's "per League" -
        # here the only league is the Eredivisie, so we group by season so the
        # percentile always compares within the same competitive sample) ---
        for temporada, df_temp in df_pos.groupby("Temporada"):
            df_temp = df_temp.copy()
            rating_cols = []
            for pilar, metrics in conf["pilares"].items():
                valid_m = [m for m in metrics if m in df_temp.columns]
                if valid_m:
                    temp_pcts = [df_temp[m].rank(pct=True) * 100 for m in valid_m]
                    pilar_pct_avg = pd.concat(temp_pcts, axis=1).mean(axis=1)
                    col_name = f"{pilar}_Rating"
                    df_temp[col_name] = pilar_pct_avg
                    rating_cols.append(col_name)

            if rating_cols:
                df_temp["Final_Score"] = df_temp[rating_cols].mean(axis=1)
                all_results.append(df_temp)

    return pd.concat(all_results, ignore_index=True) if all_results else df


def run():
    print("=== 1. Loading Wyscout files ===")
    df = cargar_todo()
    print(f"Total after minutes filter: {len(df)}")

    print("=== 2. Applying FotMob possession (and filtering out non-Eredivisie teams) ===")
    df = aplicar_posesion(df)
    print(f"Total after team filter: {len(df)}")

    print("=== 3. Normalizing positions ===")
    df = limpieza_posiciones(df)

    print("=== 4. Computing PAdj/OPAdj and per-pillar ratings ===")
    df = rankings(df)

    print(f"Final total: {len(df)}")
    print(df["Temporada"].value_counts())
    print(df["Pos_Normalizada"].value_counts())

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_parquet(OUTPUT_PATH, index=False)
    print(f"Saved to {OUTPUT_PATH}")
    return df


if __name__ == "__main__":
    run()
