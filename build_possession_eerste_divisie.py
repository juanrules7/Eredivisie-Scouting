"""
Team possession per season for the Eerste Divisie, keyed by the team names Wyscout uses.

Source: Sofascore match statistics (average of each team's per-match possession over every regular-season
match). For the Eredivisie the same computation reproduces the FotMob season figure to within 0.1 points,
so the two leagues are on the same footing.

- 2022/23 - 2025/26: mean of `possession` in Dutch-Football-Intelligence/data/processed/team_matches.csv
- 2020/21 - 2021/22: collected from Sofascore in the browser (tournament 131, seasons 29187 and 36893);
  the per-team averages are embedded below.
"""
import json
import os
import sys

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE_DIR, "data", "sofascore_possession_eerste_divisie.json")
MATCHES = os.path.join(BASE_DIR, "..", "Dutch-Football-Intelligence", "data", "processed", "team_matches.csv")

# canonical club name (Dutch-Football-Intelligence) -> Wyscout team name
CANON_TO_WYSCOUT = {
    "Jong AZ": "AZ II", "Jong Ajax": "Ajax II", "Jong PSV": "PSV II", "Jong Utrecht": "Utrecht II",
    "VVV-Venlo": "VVV Venlo",
}
# raw Sofascore name -> Wyscout team name (only the names that differ)
SOFASCORE_TO_WYSCOUT = {
    "FC Den Bosch": "Den Bosch", "FC Eindhoven": "Eindhoven", "FC Volendam": "Volendam", "FC Dordrecht": "Dordrecht",
    "SC Telstar": "Telstar", "FC Emmen": "Emmen", "Roda JC Kerkrade": "Roda JC", "Almere City FC": "Almere City",
    "MVV Maastricht": "MVV", "SC Cambuur": "Cambuur", "NEC Nijmegen": "NEC", "Jong FC Utrecht": "Utrecht II",
    "Jong AZ Alkmaar": "AZ II", "Jong PSV Eindhoven": "PSV II", "Jong Ajax": "Ajax II", "VVV-Venlo": "VVV Venlo",
}
# Wyscout labelled Jong Utrecht "Utrecht U21" in 2021/22
EXTRA_ALIASES = {"2122": {"Utrecht U21": "Utrecht II"}}

OLD_SEASONS = {  # season key -> {sofascore team: (avg possession %, matches)}
    "2122": {"FC Den Bosch": 48.9, "Helmond Sport": 46.6, "Excelsior": 49.0, "TOP Oss": 46.0, "FC Eindhoven": 43.9,
             "FC Volendam": 54.8, "FC Dordrecht": 43.9, "Jong PSV Eindhoven": 53.4, "SC Telstar": 49.7, "FC Emmen": 56.8,
             "De Graafschap": 52.7, "Roda JC Kerkrade": 53.6, "ADO Den Haag": 52.3, "Jong Ajax": 60.8,
             "Almere City FC": 50.3, "Jong FC Utrecht": 46.1, "Jong AZ Alkmaar": 51.9, "MVV Maastricht": 43.6,
             "VVV-Venlo": 43.5, "NAC Breda": 51.9},
    "2021": {"Jong FC Utrecht": 47.9, "FC Eindhoven": 46.4, "SC Cambuur": 57.6, "NEC Nijmegen": 51.1,
             "Jong PSV Eindhoven": 49.8, "Excelsior": 49.0, "NAC Breda": 46.8, "Jong AZ Alkmaar": 52.0, "TOP Oss": 45.8,
             "Helmond Sport": 48.2, "FC Dordrecht": 42.6, "Go Ahead Eagles": 49.2, "De Graafschap": 52.9,
             "FC Den Bosch": 47.2, "Almere City FC": 51.8, "MVV Maastricht": 42.1, "SC Telstar": 51.3, "Jong Ajax": 58.8,
             "Roda JC Kerkrade": 53.8, "FC Volendam": 55.7},
}
SEASON_KEY = {"22/23": "2223", "23/24": "2324", "24/25": "2425", "25/26": "2526"}


def main():
    out = {}
    for key, teams in OLD_SEASONS.items():
        out[key] = {SOFASCORE_TO_WYSCOUT.get(t, t): p for t, p in teams.items()}
        for alias, target in EXTRA_ALIASES.get(key, {}).items():
            out[key][alias] = out[key][target]

    m = pd.read_csv(MATCHES)
    m = m[m["league"] == "Eerste Divisie"]
    for season, key in SEASON_KEY.items():
        means = m[m["season"] == season].groupby("team")["possession"].mean().round(1)
        out[key] = {CANON_TO_WYSCOUT.get(t, t): float(p) for t, p in means.items()}

    out = dict(sorted(out.items()))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    for k, v in out.items():
        print(k, len(v), "teams")
    print("saved", OUT)


if __name__ == "__main__":
    sys.exit(main())
