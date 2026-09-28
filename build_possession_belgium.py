"""
Team possession per season for the Belgian Pro League, keyed by the team names Wyscout uses.

Source: Sofascore's per-team season statistics endpoint (`averageBallPossession`, already a season
average over every league match, unlike the Eerste Divisie script which had to average per-match
figures itself). Tournament id 38 ("Pro League"), season ids 77040 (25/26, complete: 16 teams) and
96616 (26/27, in progress: expanded to 18 teams - Dender relegated, Kortrijk/Lommel SK/SK Beveren
promoted from Challenger Pro League). Collected in the browser on 2026-09-28; 26/27 is a 7-round
snapshot and should be re-collected as the season goes on.
"""
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE_DIR, "data", "sofascore_possession_belgium.json")

# Sofascore team name -> Wyscout team name (only the names that differ)
SOFASCORE_TO_WYSCOUT = {
    "Royale Union Saint-Gilloise": "Union Saint-Gilloise",
    "Club Brugge KV": "Club Brugge",
    "Sint-Truidense VV": "Sint-Truiden",
    "KAA Gent": "Gent",
    "KV Mechelen": "Mechelen",
    "RSC Anderlecht": "Anderlecht",
    "KRC Genk": "Genk",
    "KVC Westerlo": "Westerlo",
    "Royal Antwerp FC": "Antwerp",
    "RC Sporting Charleroi": "Charleroi",
    "Oud-Heverlee Leuven": "OH Leuven",
    "SV Zulte Waregem": "Zulte-Waregem",
    "RAAL La Louvière": "La Louvière",
    "FCV Dender": "Dender",
    "KV Kortrijk": "Kortrijk",
    # Standard Liège, Cercle Brugge, SK Beveren, Lommel SK match Wyscout as-is.
}

SEASONS = {
    "2526": {
        "Royale Union Saint-Gilloise": 52.05, "Club Brugge KV": 60.325, "Sint-Truidense VV": 55.05,
        "KAA Gent": 49.341463414634, "KV Mechelen": 49.275, "RSC Anderlecht": 52.65,
        "KRC Genk": 58.073170731707, "Standard Liège": 44.325, "KVC Westerlo": 49.275,
        "Royal Antwerp FC": 49.425, "RC Sporting Charleroi": 49.75, "Oud-Heverlee Leuven": 45.875,
        "SV Zulte Waregem": 48.333333333333, "Cercle Brugge": 47.722222222222,
        "RAAL La Louvière": 38.777777777778, "FCV Dender": 48,
    },
    "2627": {
        "Royale Union Saint-Gilloise": 50.142857142857, "KAA Gent": 45.857142857143,
        "Club Brugge KV": 63.714285714286, "RC Sporting Charleroi": 57, "RSC Anderlecht": 61,
        "SV Zulte Waregem": 41.571428571429, "Standard Liège": 53.428571428571,
        "KVC Westerlo": 50, "KRC Genk": 51.857142857143, "SK Beveren": 49.571428571429,
        "Sint-Truidense VV": 55.142857142857, "Lommel SK": 45.857142857143,
        "Royal Antwerp FC": 48.857142857143, "RAAL La Louvière": 37.142857142857,
        "Oud-Heverlee Leuven": 48.857142857143, "KV Kortrijk": 46.571428571429,
        "Cercle Brugge": 44.714285714286, "KV Mechelen": 48.714285714286,
    },
}


def main():
    out = {}
    for key, teams in SEASONS.items():
        out[key] = {SOFASCORE_TO_WYSCOUT.get(t, t): round(float(p), 1) for t, p in teams.items()}
    out = dict(sorted(out.items()))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    for k, v in out.items():
        print(k, len(v), "teams")
    print("saved", OUT)


if __name__ == "__main__":
    sys.exit(main())
