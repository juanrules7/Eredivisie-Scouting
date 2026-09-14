"""
Descarga el historial de valor de mercado (fecha + club + valor en cada punto)
de cada jugador presente en transfer_report.parquet, desde el endpoint publico
de Transfermarkt. A diferencia de "Valor de mercado (Transfermarkt)" en los
ficheros de Wyscout (una foto actual, igual en las 4 temporadas), esto SI esta
fechado -> sirve como señal externa de si el mercado penso que un traspaso
salio bien o mal, funcione el jugador dentro o fuera de la Eredivisie.

Uso: python scrape_market_values.py  (requiere haber corrido antes
build_transfer_report.py, que es quien genera los player_id)
"""
import json
import os
import time
import urllib.request

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRANSFER_REPORT_PATH = os.path.join(BASE_DIR, "data", "transfer_report.parquet")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "market_values.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def fetch_history(player_id):
    url = f"https://www.transfermarkt.com/ceapi/marketValueDevelopment/graph/{player_id}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    points = [
        {"date": p["datum_mw"], "value_eur": p["y"], "club": p["verein"], "age": p.get("age")}
        for p in data.get("list", [])
    ]
    return points


def run():
    rep = pd.read_parquet(TRANSFER_REPORT_PATH)
    player_ids = sorted(rep["player_id"].dropna().unique().tolist())
    print(f"{len(player_ids)} jugadores unicos con player_id a scrapear")

    history = {}
    for i, pid in enumerate(player_ids):
        try:
            history[pid] = fetch_history(pid)
        except Exception as e:
            print(f"  ERROR player_id={pid}: {e}")
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(player_ids)}")
        time.sleep(0.3)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False)
    print(f"Guardado historial de {len(history)} jugadores en {OUTPUT_PATH}")


if __name__ == "__main__":
    run()
