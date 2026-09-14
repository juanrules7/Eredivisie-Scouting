"""
Joins the transfers scraped from Transfermarkt (data/transfers_raw.json) with
the processed Wyscout players (data/processed.parquet) so we can compare the
fee paid at signing vs performance (Final_Score) before/after.

Usage: python build_transfer_report.py  (requires process_data.py and
scrape_transfers.py to have run first)
"""
import json
import os
import re
import unicodedata

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRANSFERS_PATH = os.path.join(BASE_DIR, "data", "transfers_raw.json")
PROCESSED_PATH = os.path.join(BASE_DIR, "data", "processed.parquet")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "transfer_report.parquet")

# Transfermarkt uses the club's full official name in "fromClub" (e.g.
# "Excelsior Rotterdam"), but Wyscout/our "Equipo" uses the short name (e.g.
# "Excelsior") -> without this alias, an internal Eredivisie transfer wasn't
# recognized as such (is_domestic stayed False due to a naming mismatch, not
# because it genuinely came from abroad). Only FIRST TEAMS are listed here
# (not U18/U19/U21, which play in a different competition we have no data for anyway).
TM_TO_WYSCOUT_CLUB = {
    "AZ Alkmaar": "AZ",
    "Ajax Amsterdam": "Ajax",
    "Almere City FC": "Almere City",
    "Excelsior Rotterdam": "Excelsior",
    "FC Emmen": "Emmen",
    "FC Groningen": "Groningen",
    "FC Twente Enschede": "Twente",
    "FC Utrecht": "Utrecht",
    "FC Volendam": "Volendam",
    "Feyenoord Rotterdam": "Feyenoord",
    "Fortuna Sittard": "Fortuna Sittard",
    "Go Ahead Eagles": "Go Ahead Eagles",
    "Heracles Almelo": "Heracles",
    "NAC Breda": "NAC Breda",
    "NEC Nijmegen": "NEC",
    "PEC Zwolle": "PEC Zwolle",
    "PSV Eindhoven": "PSV",
    "RKC Waalwijk": "RKC Waalwijk",
    "SC Cambuur Leeuwarden": "Cambuur",
    "SC Heerenveen": "Heerenveen",
    "SC Telstar": "Telstar",
    "Sparta Rotterdam": "Sparta Rotterdam",
    "Vitesse Arnhem": "Vitesse",
    "Willem II Tilburg": "Willem II",
}


def strip_accents(s):
    if not isinstance(s, str):
        return s
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def parse_fee(text):
    t = text.strip()
    if t in ("-", "?"):
        return None, "unknown"
    if t == "free transfer":
        return 0.0, "free"
    if t == "loan transfer":
        return None, "loan"
    if t.startswith("End of loan"):
        return None, "loan_return"
    m = re.match(r"Loan fee:.(\d+(?:\.\d+)?)(m|k)", t)
    if m:
        return float(m.group(1)) * (1_000_000 if m.group(2) == "m" else 1_000), "loan_fee"
    m = re.match(r".(\d+(?:\.\d+)?)(m|k)", t)
    if m:
        return float(m.group(1)) * (1_000_000 if m.group(2) == "m" else 1_000), "fee"
    return None, "other"


def wy_name_parts(name):
    """'S. Steijn' -> ('s', 'steijn'); 'B. van Rooij' -> ('b', 'van rooij')."""
    name = name.strip()
    first_token = name.split(" ")[0]
    if "." in first_token:
        initial = name.split(".")[0].strip().lower()
        surname = name.split(".", 1)[1].strip()
    else:
        parts = name.split(" ")
        initial = parts[0][0].lower()
        surname = " ".join(parts[1:])
    return initial, strip_accents(surname).lower()


def match_transfer_to_wyscout(transfer, candidates):
    """candidates: df filtered to (Equipo, Temporada) of the transfer's destination."""
    tm_name = strip_accents(transfer["name"]).lower()
    tm_parts = tm_name.split(" ")
    tm_first, tm_last = tm_parts[0], " ".join(tm_parts[1:])
    for _, row in candidates.iterrows():
        wi, ws = wy_name_parts(row["Jugador"])
        if ws and (tm_last.endswith(ws) or ws.endswith(tm_last) or ws in tm_last):
            if tm_first.startswith(wi):
                return row["Jugador"]
    return None


def run():
    with open(TRANSFERS_PATH, encoding="utf-8") as f:
        transfers = json.load(f)
    for t in transfers:
        t["fee_eur"], t["fee_type"] = parse_fee(t["feeText"])

    df = pd.read_parquet(PROCESSED_PATH)

    rows = []
    for t in transfers:
        candidates = df[(df["Equipo"] == t["club"]) & (df["Temporada"] == t["season"])]
        if candidates.empty:
            continue
        wy_name = match_transfer_to_wyscout(t, candidates)
        if not wy_name:
            continue

        latest = df[df["Jugador"] == wy_name].iloc[-1]
        procedencia_wyscout = TM_TO_WYSCOUT_CLUB.get(t["fromClub"])

        rows.append({
            "Jugador": wy_name,
            "player_id": t.get("player_id"),
            "Club_destino": t["club"],
            "Temporada_fichaje": t["season"],
            "Procedencia": t["fromClub"],
            "Procedencia_Wyscout": procedencia_wyscout,
            "Liga_procedencia": t["fromLeague"],
            "Fee_EUR": t["fee_eur"],
            "Fee_tipo": t["fee_type"],
            "Posicion": latest["Pos_Normalizada"],
            # Internal Eredivisie transfer -> we have real stats from BEFORE and
            # AFTER (same pipeline, same methodology) and can explain the "why"
            # pillar by pillar. If they came from abroad, we don't have their
            # prior season and only market value is left as an external clue.
            "is_domestic": procedencia_wyscout is not None,
        })

    rep = pd.DataFrame(rows)
    rep.to_parquet(OUTPUT_PATH, index=False)
    print(f"{len(rep)} transfers matched to Wyscout out of {len(transfers)} scraped")
    print(f"  of which {rep['is_domestic'].sum()} are internal Eredivisie transfers")
    print(f"Saved to {OUTPUT_PATH}")
    return rep


if __name__ == "__main__":
    run()
