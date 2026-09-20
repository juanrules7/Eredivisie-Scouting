"""
Wyscout data processing pipeline for the Dutch leagues: Eredivisie (2022/23 - 2025/26)
and Eerste Divisie (2020/21 - 2026/27, the last one still in progress).
Replicates the logic of scouting_general.py (loading, minutes filter, team
possession, position normalization, PAdj/OPAdj adjustment and per-pillar
percentiles). Percentiles are computed within league + season + position.
"""
import json
import os
import re

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
# Eredivisie possession: FotMob. Eerste Divisie possession: Sofascore (build_possession_eerste_divisie.py).
POSSESSION_PATHS = {
    "Eredivisie": os.path.join(BASE_DIR, "data", "fotmob_possession.json"),
    "Eerste Divisie": os.path.join(BASE_DIR, "data", "sofascore_possession_eerste_divisie.json"),
}
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "processed.parquet")

MIN_MINUTES = 900
PERIOD_COL = "Equipo durante el período seleccionado"

FILES = [
    ("DEF_MID_GK 2526.xlsx", "25/26", "Eredivisie"),
    ("ATT 2526.xlsx", "25/26", "Eredivisie"),
    ("DEF_MID_GK 2425.xlsx", "24/25", "Eredivisie"),
    ("ATT 2425.xlsx", "24/25", "Eredivisie"),
    ("DEF_MID_GK 2324.xlsx", "23/24", "Eredivisie"),
    ("ATT 2324.xlsx", "23/24", "Eredivisie"),
    ("DEF_MID_GK 2223.xlsx", "22/23", "Eredivisie"),
    ("ATT 2223.xlsx", "22/23", "Eredivisie"),
    ("EERSTE DEF_MID_GK 2627.xlsx", "26/27", "Eerste Divisie"),
    ("EERSTE ATT 2627.xlsx", "26/27", "Eerste Divisie"),
    ("EERSTE DEF_MID_GK 2526.xlsx", "25/26", "Eerste Divisie"),
    ("EERSTE ATT 2526.xlsx", "25/26", "Eerste Divisie"),
    ("EERSTE DEF_MID_GK 2425.xlsx", "24/25", "Eerste Divisie"),
    ("EERSTE ATT 2425.xlsx", "24/25", "Eerste Divisie"),
    ("EERSTE DEF_MID_GK 2324.xlsx", "23/24", "Eerste Divisie"),
    ("EERSTE ATT 2324.xlsx", "23/24", "Eerste Divisie"),
    ("EERSTE DEF_MID_GK 2223.xlsx", "22/23", "Eerste Divisie"),
    ("EERSTE ATT 2223.xlsx", "22/23", "Eerste Divisie"),
    ("EERSTE DEF_MID_GK 2122.xlsx", "21/22", "Eerste Divisie"),
    ("EERSTE ATT 2122.xlsx", "21/22", "Eerste Divisie"),
    ("EERSTE DEF_MID_GK 2021.xlsx", "20/21", "Eerste Divisie"),
    ("EERSTE ATT 2021.xlsx", "20/21", "Eerste Divisie"),
]

# Seasons still being played: the 900-minute bar is scaled to the games each team has played so far
# (900 minutes over a 38-game season = 900/38 minutes per game played).
PARTIAL_SEASONS = {("Eerste Divisie", "26/27"): 38}   # (league, season) -> season length in games

# "25/26" -> "2526"
def season_key(temporada):
    return temporada.replace("/", "")

# ==========================================
# 1. LOAD FILES AND FILTER BY MINUTES
# ==========================================
def cargar_todo():
    raw = []
    for fname, temporada, liga in FILES:
        path = os.path.join(RAW_DIR, fname)
        if not os.path.exists(path):
            print(f"WARNING: not found {path}")
            continue
        df = pd.read_excel(path)
        df["Temporada"] = temporada
        df["Liga"] = liga
        raw.append((fname, temporada, liga, df))

    # games played so far by each team of a season in progress = most games any of its players has played
    team_games = {}
    for _f, temporada, liga, df in raw:
        if (liga, temporada) in PARTIAL_SEASONS:
            team = df[PERIOD_COL].fillna(df["Equipo"]) if PERIOD_COL in df.columns else df["Equipo"]
            for t, g in df.groupby(team)["Partidos jugados"].max().items():
                team_games[(liga, temporada, t)] = max(g, team_games.get((liga, temporada, t), 0))

    frames = []
    for fname, temporada, liga, df in raw:
        if "Minutos jugados" in df.columns:
            if (liga, temporada) in PARTIAL_SEASONS:
                season_len = PARTIAL_SEASONS[(liga, temporada)]
                team = df[PERIOD_COL].fillna(df["Equipo"]) if PERIOD_COL in df.columns else df["Equipo"]
                bar = team.map(lambda t: MIN_MINUTES * team_games.get((liga, temporada, t), 0) / season_len)
                df = df[df["Minutos jugados"] >= bar].copy()
                print(f"  Loaded {liga} {fname}: {len(df)} players (season in progress: minutes bar scaled to games played, "
                      f"{MIN_MINUTES / season_len:.1f} min per game)")
            else:
                df = df[df["Minutos jugados"] >= MIN_MINUTES].copy()
                print(f"  Loaded {liga} {fname}: {len(df)} players with >= {MIN_MINUTES} min")
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


# ==========================================
# 2. POSSESSION PER TEAM, LEAGUE AND SEASON
# ==========================================
def aplicar_posesion(df):
    possession = {}
    for liga, path in POSSESSION_PATHS.items():
        with open(path, "r", encoding="utf-8") as f:
            possession[liga] = json.load(f)

    df = df.copy()
    if PERIOD_COL in df.columns:
        df["Equipo"] = df[PERIOD_COL].fillna(df["Equipo"])

    def lookup(row):
        mapa = possession.get(row["Liga"], {}).get(season_key(row["Temporada"]), {})
        return mapa.get(row["Equipo"])

    df["team_possession"] = df.apply(lookup, axis=1)

    before = len(df)
    df = df.dropna(subset=["team_possession"]).copy()
    removed = before - len(df)
    print(f"Possession applied. Removed {removed} player(s) whose team wasn't in the "
          f"possession map (Eredivisie reserve sides, loans to clubs outside the two leagues, etc.)")
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

        # --- RATING PER LEAGUE AND SEASON (equivalent to the original pipeline's "per League":
        # the percentile always compares within the same competitive sample) ---
        for (_liga, temporada), df_temp in df_pos.groupby(["Liga", "Temporada"]):
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

    print("=== 2. Applying possession (FotMob for the Eredivisie, Sofascore for the Eerste Divisie) ===")
    df = aplicar_posesion(df)
    print(f"Total after team filter: {len(df)}")

    print("=== 3. Normalizing positions ===")
    df = limpieza_posiciones(df)

    print("=== 4. Computing PAdj/OPAdj and per-pillar ratings ===")
    df = rankings(df)

    print(f"Final total: {len(df)}")
    print(df.groupby(["Liga", "Temporada"]).size())
    print(df["Pos_Normalizada"].value_counts())

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_parquet(OUTPUT_PATH, index=False)
    print(f"Saved to {OUTPUT_PATH}")
    return df


if __name__ == "__main__":
    run()
