"""
Visualization and analysis functions for the Eredivisie dashboard.
Direct port of the functions in scouting_general.py (the same dashboard
already used for Spain/Europe), adapted to a single-league (Eredivisie)
dataset spanning 4 seasons instead of multiple leagues.

The only real differences from the original:
  - plot_similar_players_cross_st and plot_market_analysis_st no longer
    filter by a fixed "top 5 leagues" list (Spain/England/Germany/Italy/
    France): with a single league in the dataset, the reference population
    is always the whole dataframe passed in.
  - Everything else (formulas, column names, chart styling) is identical
    to the original so behavior stays the same.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import Radar
from sklearn.metrics.pairwise import cosine_similarity


def plot_omni_radar_evolutivo(players_list):
    """Radar chart for 1-3 players. Only uses non-NaN _Rating columns so each
    position shows its own specific pillars (not all positions mixed together)."""
    extracted_data, labels = [], []

    for name, df, label in players_list:
        try:
            row = df[df['Jugador'] == name].iloc[0]
            extracted_data.append(row)
            labels.append(label)
        except (IndexError, KeyError):
            continue

    if not extracted_data:
        return None

    pilares_cols = [
        c for c in extracted_data[0].index
        if '_Rating' in c and pd.notna(extracted_data[0][c])
    ]

    if len(pilares_cols) < 3:
        return None

    params = [c.replace('_Rating', '') for c in pilares_cols]
    low = [0] * len(params)
    high = [100] * len(params)

    values = []
    for p in extracted_data:
        row_vals = [float(p[c]) if pd.notna(p[c]) else 0.0 for c in pilares_cols]
        values.append(row_vals)

    colors = ['#77BA99', '#e63946', '#F3E03B']  # green, red, yellow

    try:
        radar = Radar(params, low, high, round_int=[False] * len(params),
                      num_rings=5, center_circle_radius=1)
    except TypeError:
        radar = Radar(params, low, high, num_rings=5, center_circle_radius=1)

    fig, ax = radar.setup_axis()
    radar.draw_circles(ax=ax, facecolor='#f5f5f5', edgecolor='#cccccc', zorder=1)

    for i, (val, color) in enumerate(zip(values, colors)):
        alpha = 0.4 if len(values) > 1 else 0.5
        result = radar.draw_radar(
            ax=ax, values=val,
            kwargs_radar={'facecolor': color, 'alpha': alpha},
            kwargs_rings={'facecolor': color, 'alpha': 0.1}
        )
        try:
            polygon = result[0] if isinstance(result, tuple) else result
            verts = polygon.get_path().vertices
            n = len(params)
            use_verts = verts[:n] if len(verts) > n else verts
            for j, (vx, vy) in enumerate(use_verts):
                if j < len(val):
                    ax.text(vx, vy, f"{val[j]:.0f}",
                            fontsize=8, ha='center', va='center',
                            color='white', fontweight='bold', zorder=15,
                            bbox=dict(boxstyle='round,pad=0.15',
                                      facecolor=color, alpha=0.9, edgecolor='none'))
        except Exception:
            pass

    radar.draw_range_labels(ax=ax, fontsize=9, fontproperties="monospace", zorder=12)
    radar.draw_param_labels(ax=ax, fontsize=11, fontproperties="monospace",
                             fontweight='bold', zorder=12)

    if len(labels) == 1:
        ax.text(0.5, 1.02, labels[0], fontsize=16, color=colors[0],
                ha='center', va='center', transform=ax.transAxes,
                fontfamily='monospace', fontweight='bold')
    elif len(labels) == 2:
        ax.text(0.3, 1.02, labels[0], fontsize=14, color=colors[0],
                ha='center', va='center', transform=ax.transAxes,
                fontfamily='monospace', fontweight='bold')
        ax.text(0.5, 1.02, 'vs', fontsize=14, color='black',
                ha='center', va='center', transform=ax.transAxes,
                fontfamily='monospace')
        ax.text(0.7, 1.02, labels[1], fontsize=14, color=colors[1],
                ha='center', va='center', transform=ax.transAxes,
                fontfamily='monospace', fontweight='bold')
    elif len(labels) >= 3:
        ax.text(0.15, 1.02, labels[0], fontsize=11, color=colors[0],
                ha='center', va='center', transform=ax.transAxes,
                fontfamily='monospace', fontweight='bold')
        ax.text(0.35, 1.02, 'vs', fontsize=11, color='black',
                ha='center', va='center', transform=ax.transAxes,
                fontfamily='monospace')
        ax.text(0.5, 1.02, labels[1], fontsize=11, color=colors[1],
                ha='center', va='center', transform=ax.transAxes,
                fontfamily='monospace', fontweight='bold')
        ax.text(0.65, 1.02, 'vs', fontsize=11, color='black',
                ha='center', va='center', transform=ax.transAxes,
                fontfamily='monospace')
        ax.text(0.85, 1.02, labels[2], fontsize=11, color=colors[2],
                ha='center', va='center', transform=ax.transAxes,
                fontfamily='monospace', fontweight='bold')

    ax.text(0.0, -0.1,
            'Ratings: Based on percentiles (0-100)\nPossession-Adjusted',
            fontsize=9, ha='left', va='center', transform=ax.transAxes,
            fontfamily='monospace', color='#555555')
    return fig


def aplicar_filtros_scouting_st(df_temporada, filtros):
    """Filters a season DataFrame according to a {metric_Rating: minimum} dict."""
    if df_temporada is None or df_temporada.empty:
        return pd.DataFrame()

    df_res = df_temporada.copy()
    for columna, valor_minimo in filtros.items():
        if valor_minimo > 0:
            if columna in df_res.columns:
                df_res = df_res[df_res[columna] >= valor_minimo]
            else:
                continue

    if 'Final_Score' in df_res.columns:
        df_res = df_res.sort_values(by='Final_Score', ascending=False)

    return df_res


def plot_similar_players_cross_st(player_name, df_origen, df_destino, top_n=10):
    features = [c for c in df_origen.columns if "_Rating" in c]
    features = [f for f in features if f in df_destino.columns]

    if player_name not in df_origen['Jugador'].values:
        return None

    # Con una sola liga en el dataset, la poblacion de referencia es
    # siempre el dataframe destino completo (sin filtro de "top 5 ligas").
    df_destino_filt = df_destino.copy()

    target_vector = df_origen[df_origen['Jugador'] == player_name][features].fillna(0).values
    candidatos_matrix = df_destino_filt[features].fillna(0).values

    try:
        sim_scores_array = cosine_similarity(target_vector, candidatos_matrix)[0]
        sim_scores = sorted(list(enumerate(sim_scores_array)), key=lambda x: x[1], reverse=True)

        final_sim_scores = []
        for i, score in sim_scores:
            nombre_candidato = df_destino_filt.iloc[i]['Jugador']
            if nombre_candidato == player_name and score > 0.99:
                continue
            final_sim_scores.append((i, score))
            if len(final_sim_scores) >= top_n:
                break

        names = []
        for i, _ in final_sim_scores:
            p_name = df_destino_filt.iloc[i]['Jugador']
            p_team = df_destino_filt.iloc[i]['Equipo']
            names.append(f"{p_name} ({p_team})")

        similarities = [score * 100 for _, score in final_sim_scores]

        if not names:
            return None

        fig, ax = plt.subplots(figsize=(10, 6), facecolor='#ffffff')
        bars = ax.barh(names, similarities, color='#D4AF37', edgecolor='black', alpha=0.8)
        ax.invert_yaxis()
        ax.set_xlim(max(0, min(similarities) - 10), 105)
        ax.set_title(f"Statistical Twins: Players similar to {player_name}", fontweight='bold', pad=20)

        for bar in bars:
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                    f'{bar.get_width():.1f}%', va='center', fontweight='bold')

        plt.tight_layout()
        return fig
    except Exception as e:
        print(f"Similarity error: {e}")
        return None


def plot_zscore_st(lista_jugadores, titulo="Comparativa Z-Score"):
    player_data_list, pilares_cols = [], []
    for nombre, df_origen in lista_jugadores:
        if df_origen.empty:
            continue
        if not pilares_cols:
            pilares_cols = [c for c in df_origen.columns if '_Rating' in c]
        df_z = df_origen.copy()
        for col in pilares_cols:
            df_z[f'z_{col}'] = (df_z[col] - df_z.groupby('Liga')[col].transform('mean')) / (
                df_z.groupby('Liga')[col].transform('std') + 1e-6)
        try:
            player_data_list.append(df_z[df_z['Jugador'] == nombre].iloc[0])
        except Exception:
            continue

    if not player_data_list:
        return None
    params = [c.replace('_Rating', '') for c in pilares_cols]
    fig, ax = plt.subplots(figsize=(10, 7))
    y = np.arange(len(params))
    height = 0.8 / len(player_data_list)
    colors = ['#77BA99', '#E84855', '#3182CE']
    for i, data in enumerate(player_data_list):
        z_vals = [data[f'z_{col}'] for col in pilares_cols]
        ax.barh(y + (i - (len(player_data_list) - 1) / 2) * height, z_vals, height,
                label=data['Jugador'], color=colors[i % 3])
    ax.axvline(0, color='black', lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels(params, fontweight='bold')
    ax.legend()
    return fig


def plot_market_analysis_st(df_temporada, target_player, metrics, titulo_temp=""):
    if df_temporada is None or df_temporada.empty:
        return None

    df_plot = df_temporada.copy()
    col_age = 'Edad' if 'Edad' in df_temporada.columns else 'Age'
    col_name = 'Jugador' if 'Jugador' in df_temporada.columns else 'Name'

    df_plot['Combined'] = df_plot[metrics].mean(axis=1).fillna(0)

    # Una sola liga en el dataset -> la poblacion de referencia es todo el df.
    df_poblacion = df_plot.copy()

    df_target = df_plot[df_plot[col_name] == target_player].copy()

    fig, ax = plt.subplots(figsize=(12, 8), facecolor='#FCF9F0')
    ax.set_facecolor('#FCF9F0')

    u23_ref = df_poblacion[df_poblacion[col_age] <= 23]
    vets_ref = df_poblacion[df_poblacion[col_age] > 23]

    ax.scatter(vets_ref[col_age], vets_ref['Combined'],
               color='#d3d3d3', alpha=0.4, s=60, label='Veterans')
    ax.scatter(u23_ref[col_age], u23_ref['Combined'],
               color='#5DA5DA', alpha=0.8, s=120, edgecolor='black', lw=1.2, label='U23')

    if not df_target.empty:
        p = df_target.iloc[0]
        ax.scatter(p[col_age], p['Combined'],
                   color='#FDD835', s=600, marker='*', edgecolor='black', zorder=15,
                   label=f'TARGET: {target_player}')

        df_poblacion['dist'] = np.sqrt(
            (df_poblacion[col_age] - p[col_age]) ** 2 + (df_poblacion['Combined'] - p['Combined']) ** 2)
        closest = df_poblacion[df_poblacion[col_name] != target_player].sort_values('dist').head(6)

        for _, row in closest.iterrows():
            ax.text(row[col_age], row['Combined'] + 1.8, row[col_name],
                    fontsize=8.5, ha='center', fontweight='bold', color='#333333',
                    bbox=dict(facecolor='white', alpha=0.5, edgecolor='none', boxstyle='round,pad=0.2'))

    mean_combined = df_poblacion['Combined'].mean()
    ax.axhline(mean_combined, color='gray', linestyle=(0, (1, 10)), lw=1.5, alpha=0.6, label='Mean')
    ax.axvline(23.5, color='#F8BBD0', linestyle=(0, (5, 5)), lw=1.5, alpha=0.8)

    ax.set_title(f'Market Positioning {titulo_temp}: {target_player}', fontsize=16, fontweight='bold', pad=30)
    ax.set_xlabel('Age', fontsize=11, labelpad=10)
    nombre_metrica_y = 'Combined Rating (Ratings)'
    if len(metrics) > 0:
        nombres_c = [m.replace('_Rating', '') for m in metrics]
        nombre_metrica_y = f'{" + ".join(nombres_c)}'
    ax.set_ylabel(f'Combined Rating ({nombre_metrica_y})', fontsize=11, labelpad=10)

    ax.legend(loc='lower right', facecolor='white', frameon=True, fontsize=10)
    sns.despine(left=True, bottom=True)
    plt.tight_layout()

    return fig


def get_player_bio_card(df, player_name):
    try:
        row = df[df['Jugador'] == player_name].iloc[0]
        ratings = {c.replace('_Rating', ''): row[c] for c in df.columns if '_Rating' in c}
        top_3 = sorted(ratings.items(), key=lambda x: x[1], reverse=True)[:3]

        return {
            "Equipo": row['Equipo'],
            "Liga": row['Liga'],
            "Edad": int(row['Edad']),
            "Score": round(row['Final_Score'], 1),
            "Top Virtudes": top_3
        }
    except Exception:
        return None


def plot_league_rank_st(df, player_name):
    try:
        row_target = df[df['Jugador'] == player_name].iloc[0]
        liga_target = row_target['Liga']

        df_liga = df[df['Liga'] == liga_target].copy()
        # Only pillars that apply to this player's position (avoids NaN ->
        # int() from another position's pillars, e.g. goalkeeper pillars on
        # an outfield player, which would be NaN after concatenating all
        # positions together).
        metrics = [c for c in df.columns if '_Rating' in c and pd.notna(row_target[c])]

        ranks = []
        for m in metrics:
            df_liga[f'rank_{m}'] = df_liga[m].rank(ascending=False)
            pos = int(df_liga[df_liga['Jugador'] == player_name][f'rank_{m}'].iloc[0])
            total = len(df_liga)
            percentile = (row_target[m])
            ranks.append({'Metrica': m.replace('_Rating', ''), 'Posicion': pos, 'Total': total, 'Valor': percentile})

        df_rank = pd.DataFrame(ranks).sort_values('Valor', ascending=True)

        fig, ax = plt.subplots(figsize=(8, 6))
        colors = plt.cm.RdYlGn(np.array(df_rank['Valor']) / 100)
        bars = ax.barh(df_rank['Metrica'], df_rank['Valor'], color=colors, edgecolor='black', alpha=0.7)

        for i, bar in enumerate(bars):
            ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                    f"Rank: {df_rank.iloc[i]['Posicion']} of {df_rank.iloc[i]['Total']}",
                    va='center', fontweight='bold', fontsize=9)

        ax.set_xlim(0, 115)
        ax.set_title(f"Performance vs {liga_target}", fontsize=12, fontweight='bold')
        sns.despine(left=True, bottom=True)
        return fig
    except Exception:
        return None


SEASON_ORDER = ["22/23", "23/24", "24/25", "25/26"]
SEASON_PREV = {"23/24": "22/23", "24/25": "23/24", "25/26": "24/25"}


def get_transfer_before_after(df, jugador, procedencia_wyscout, club_destino, temporada_fichaje):
    """
    Internal Eredivisie transfer -> looks up the real BEFORE row (previous
    season at the origin club) and AFTER row (first available season at the
    destination club) in our own data. Returns (before_row, after_row,
    prev_season), or (None, ..., None) if there's no prior season with data
    (e.g. the transfer happened in 22/23, the first year in this dataset).
    """
    hist = df[df["Jugador"] == jugador]

    before_row = None
    prev_season = SEASON_PREV.get(temporada_fichaje)
    if prev_season:
        before_match = hist[(hist["Equipo"] == procedencia_wyscout) & (hist["Temporada"] == prev_season)]
        if not before_match.empty:
            before_row = before_match.iloc[0]

    after_candidates = hist[
        (hist["Equipo"] == club_destino)
        & (hist["Temporada"].map({s: i for i, s in enumerate(SEASON_ORDER)}) >=
           SEASON_ORDER.index(temporada_fichaje))
    ].sort_values("Temporada", key=lambda s: s.map({v: i for i, v in enumerate(SEASON_ORDER)}))
    after_row = after_candidates.iloc[0] if not after_candidates.empty else None

    return before_row, after_row, prev_season


def plot_transfer_pillar_comparison(before_row, after_row):
    """
    Compares performance before and after an internal Eredivisie transfer
    pillar by pillar (not one blended number). Only includes pillars that
    exist (non-NaN) in BOTH rows, so different position profiles aren't
    compared if the player changed role.
    """
    if before_row is None or after_row is None:
        return None

    pilares = [
        c.replace('_Rating', '') for c in before_row.index
        if c.endswith('_Rating') and pd.notna(before_row[c]) and c in after_row.index and pd.notna(after_row[c])
    ]
    if not pilares:
        return None

    before_vals = [before_row[f"{p}_Rating"] for p in pilares]
    after_vals = [after_row[f"{p}_Rating"] for p in pilares]

    order = sorted(range(len(pilares)), key=lambda i: after_vals[i] - before_vals[i])
    pilares = [pilares[i] for i in order]
    before_vals = [before_vals[i] for i in order]
    after_vals = [after_vals[i] for i in order]

    fig, ax = plt.subplots(figsize=(9, max(4, 0.5 * len(pilares))))
    y = np.arange(len(pilares))
    height = 0.35
    ax.barh(y - height / 2, before_vals, height, label=f"{before_row['Equipo']} ({before_row['Temporada']})",
            color='#9e9e9e', edgecolor='black')
    ax.barh(y + height / 2, after_vals, height, label=f"{after_row['Equipo']} ({after_row['Temporada']})",
            color='#4C72B0', edgecolor='black')
    ax.set_yticks(y)
    ax.set_yticklabels(pilares)
    ax.set_xlim(0, 105)
    ax.set_xlabel('Percentile (0-100, within position & season)')
    ax.legend(loc='lower right')
    ax.set_title('Before vs after the transfer, pillar by pillar', fontsize=13, fontweight='bold')
    sns.despine(left=True, bottom=True)
    plt.tight_layout()
    return fig


def plot_market_value_trend(history, transfer_date=None, transfer_fee=None, player_name=""):
    """
    history: list of {date, value_eur, club, age} exactly as returned by
    Transfermarkt's public marketValueDevelopment endpoint. Works the same
    whether the player played in or outside the Eredivisie -> it's the only
    signal we have for those cases (doesn't say "why" but does say "did it work").
    """
    if not history:
        return None

    dates = pd.to_datetime([h['date'] for h in history], format='%d/%m/%Y', errors='coerce')
    values = [h['value_eur'] / 1e6 for h in history]
    clubs = [h['club'] for h in history]

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(dates, values, marker='o', color='#4C72B0', lw=2, zorder=3)

    prev_club = None
    for d, v, c in zip(dates, values, clubs):
        if c != prev_club:
            ax.annotate(c, (d, v), fontsize=7.5, rotation=30, ha='left', va='bottom',
                        xytext=(2, 4), textcoords='offset points', color='#555555')
            prev_club = c

    if transfer_date is not None:
        ax.axvline(transfer_date, color='#e63946', linestyle='--', lw=1.5, zorder=2)
        label = 'Eredivisie signing'
        if transfer_fee:
            label += f' (€{transfer_fee/1e6:.1f}M)'
        ax.text(transfer_date, max(values) * 1.02, label, color='#e63946',
                fontsize=9, fontweight='bold', ha='center')

    ax.set_ylabel('Market value (€M)')
    ax.set_title(f'Market value over time — {player_name}', fontsize=13, fontweight='bold')
    sns.despine(left=True)
    plt.tight_layout()
    return fig
