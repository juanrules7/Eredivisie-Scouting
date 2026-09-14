"""
Scrapes the arrivals history of every Eredivisie club in each of the 4
seasons (22/23-25/26) from Transfermarkt: date/season, origin club, fee
paid. Saves the raw result to data/transfers_raw.json.

Usage: python scrape_transfers.py
"""
import json
import os
import re
import time
import urllib.request

from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "transfers_raw.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

CLUB_IDS = {
    "Ajax": 610, "AZ": 1090, "Feyenoord": 234, "Twente": 317, "Utrecht": 200,
    "Heerenveen": 306, "NEC": 467, "Groningen": 202, "Sparta Rotterdam": 468,
    "PEC Zwolle": 1269, "Go Ahead Eagles": 1435, "Willem II": 403,
    "Excelsior": 798, "Fortuna Sittard": 385, "Cambuur": 133, "Telstar": 1434,
    "PSV": 383, "NAC Breda": 132, "Heracles": 1304, "RKC Waalwijk": 235,
    "Volendam": 724, "Vitesse": 499, "Emmen": 1283, "Almere City": 723,
}

# Same rosters used in process_data.py / aplicar_posesion (a club is only
# scraped for the seasons it actually played in the Eredivisie).
ROSTERS = {
    "25/26": ["AZ", "Ajax", "Excelsior", "Feyenoord", "Fortuna Sittard", "Go Ahead Eagles",
              "Groningen", "Heerenveen", "Heracles", "NAC Breda", "NEC", "PEC Zwolle", "PSV",
              "Sparta Rotterdam", "Telstar", "Twente", "Utrecht", "Volendam"],
    "24/25": ["Ajax", "Almere City", "AZ", "Feyenoord", "Fortuna Sittard", "Go Ahead Eagles",
              "Groningen", "Heerenveen", "Heracles", "NAC Breda", "NEC", "PEC Zwolle", "PSV",
              "RKC Waalwijk", "Sparta Rotterdam", "Twente", "Utrecht", "Willem II"],
    "23/24": ["Ajax", "Almere City", "AZ", "Excelsior", "Feyenoord", "Fortuna Sittard",
              "Go Ahead Eagles", "Heerenveen", "Heracles", "NEC", "PEC Zwolle", "PSV",
              "RKC Waalwijk", "Sparta Rotterdam", "Twente", "Utrecht", "Vitesse", "Volendam"],
    "22/23": ["Ajax", "AZ", "Cambuur", "Emmen", "Excelsior", "Feyenoord", "Fortuna Sittard",
              "Go Ahead Eagles", "Groningen", "Heerenveen", "NEC", "PSV", "RKC Waalwijk",
              "Sparta Rotterdam", "Twente", "Utrecht", "Vitesse", "Volendam"],
}

SEASON_TO_SAISON_ID = {"25/26": 2025, "24/25": 2024, "23/24": 2023, "22/23": 2022}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_arrivals(html, club, season):
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for box in soup.select(".box"):
        h2 = box.find("h2")
        if not h2 or "arrivals" not in h2.get_text(strip=True).lower():
            continue
        for row in box.select("table.items > tbody > tr"):
            tds = [c for c in row.find_all("td", recursive=False)]
            if len(tds) < 6:
                continue
            name_a = tds[1].select_one("a[title]")
            if not name_a:
                continue
            name = name_a["title"]
            player_id_m = re.search(r"/spieler/(\d+)", name_a.get("href", ""))
            player_id = player_id_m.group(1) if player_id_m else None
            pos_rows = tds[1].find_all("tr")
            position = pos_rows[1].get_text(strip=True) if len(pos_rows) > 1 else ""
            age = tds[2].get_text(strip=True)
            from_a = tds[4].select_one("a[title]")
            from_club = from_a["title"] if from_a else tds[4].get_text(strip=True)
            from_league_links = tds[4].find_all("a")
            from_league = from_league_links[1].get_text(strip=True) if len(from_league_links) > 1 else ""
            fee_text = tds[5].get_text(strip=True)
            results.append({
                "club": club, "season": season, "name": name, "player_id": player_id,
                "position": position, "age": age, "fromClub": from_club,
                "fromLeague": from_league, "feeText": fee_text,
            })
    return results


def run():
    all_results = []
    for season, clubs in ROSTERS.items():
        saison_id = SEASON_TO_SAISON_ID[season]
        for club in clubs:
            club_id = CLUB_IDS[club]
            url = f"https://www.transfermarkt.com/x/transfers/verein/{club_id}/saison_id/{saison_id}"
            try:
                html = fetch(url)
                rows = parse_arrivals(html, club, season)
                all_results.extend(rows)
                print(f"  {season} {club}: {len(rows)} arrivals")
            except Exception as e:
                print(f"  ERROR {season} {club}: {e}")
            time.sleep(0.5)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False)
    print(f"\nTotal: {len(all_results)} rows saved to {OUTPUT_PATH}")
    return all_results


if __name__ == "__main__":
    run()
