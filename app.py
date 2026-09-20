import io
import json
import os

import pandas as pd
import streamlit as st

import scouting_ned as sg

# 1. Page Configuration
st.set_page_config(page_title="Dutch Football Scouting", layout="wide", page_icon="⚽")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "processed.parquet")
TRANSFERS_PATH = os.path.join(BASE_DIR, "data", "transfer_report.parquet")
MARKET_VALUES_PATH = os.path.join(BASE_DIR, "data", "market_values.json")

LEAGUES = ["Eredivisie", "Eerste Divisie"]
SEASONS_BY_LEAGUE = {
    "Eredivisie": ["25/26", "24/25", "23/24", "22/23"],
    "Eerste Divisie": ["25/26", "24/25", "23/24", "22/23", "21/22", "20/21"],
}
# Transfers / Transfer Deep Dive are scraped for Eredivisie arrivals only
SEASONS_ERE = SEASONS_BY_LEAGUE["Eredivisie"]

# 2. Initial Data Loading & Session State Management
if "df_all" not in st.session_state:
    with st.spinner("Loading data and calculating performance ranks..."):
        st.session_state.df_all = pd.read_parquet(DATA_PATH)
        st.session_state.df_transfers = (
            pd.read_parquet(TRANSFERS_PATH) if os.path.exists(TRANSFERS_PATH) else pd.DataFrame()
        )
        if os.path.exists(MARKET_VALUES_PATH):
            with open(MARKET_VALUES_PATH, encoding="utf-8") as f:
                st.session_state.market_values = json.load(f)
        else:
            st.session_state.market_values = {}


def season_df(temporada: str) -> pd.DataFrame:
    """Players of the league selected in the sidebar for one season."""
    df = st.session_state.df_all
    return df[(df["Liga"] == league) & (df["Temporada"] == temporada)]


# --- App Header ---
st.title("⚽ Dutch Football Scouting Platform")
st.caption("Wyscout data · Eredivisie 2022/23 – 2025/26 · Eerste Divisie 2020/21 – 2025/26 · minimum 900 minutes played")
st.markdown("---")

# --- METHODOLOGY SECTION ---
with st.expander("📖 READ FIRST: Methodology, Calibration & PAdj Logic", expanded=True):
    st.markdown("### 📊 How Rankings Work")
    st.write("""
    Rankings are computed as **pure within-league, within-season percentiles**. Each player is ranked
    against their positional peers in the same league and season, ensuring that the scores reflect genuine
    performance relative to the competition they actually faced that year. A 90 in the Eerste Divisie is
    a 90 among Eerste Divisie players, **not** equivalent to a 90 in the Eredivisie.
    """)
    st.markdown("### ⚖️ Possession Adjustment (PAdj)")
    st.write("""
    To ensure this analysis reflects true technical quality rather than team style, all data has been
    **Possession-Adjusted (PAdj)**, using each team's average possession % for that league and season
    (FotMob for the Eredivisie, Sofascore for the Eerste Divisie; where both were checked they agree to
    within 0.1 points).
    Standard 'Per 90' metrics are often misleading because they fail to account for the 'opportunity' a
    player has to act — a defender on a team with 70% possession has far fewer chances to make tackles
    than one on a team with 30%. By adjusting for possession, we normalize the environment, allowing us
    to compare a player's output as if every player operated under a balanced **50% possession split**.
    """)
    st.markdown("### 📊 Percentile Calculation")
    st.write("""
    Beyond volume, these PAdj metrics are combined with **success rates** to generate comprehensive
    percentiles, so a high ranking reflects **efficiency**, not just activity. Only players with **900+
    minutes played** in a given season are included, so small samples don't distort the scale.
    The Eerste Divisie includes the four reserve sides (shown as Ajax II, PSV II, AZ II, Utrecht II)
    because they play in that league and its possession figures are available.
    """)

st.markdown("---")

# 3. Sidebar (Global Filters)
st.sidebar.header("🔍 Global Search Filters")

if st.sidebar.button("🔄 Clear Cache & Reload Data"):
    for key in ["df_all", "df_transfers", "market_values"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

league = st.sidebar.radio("League", LEAGUES)
SEASONS = SEASONS_BY_LEAGUE[league]
temp_choice = st.sidebar.selectbox("Season", SEASONS)
df_actual = season_df(temp_choice)

posiciones = sorted(df_actual["Pos_Normalizada"].unique())
pos_select = st.sidebar.multiselect("Filter by Position", posiciones)

# 4. Global Filtering Logic
df_display = df_actual
if pos_select:
    df_display = df_display[df_display["Pos_Normalizada"].isin(pos_select)]

# 5. Main Dashboard Ranking
st.subheader(f"Identified Players: {league} ({temp_choice})")

col_score = "Final_Score"
if col_score in df_display.columns:
    df_ranked = df_display.sort_values(by=col_score, ascending=False)

    display_cols = {
        "Jugador": "Player",
        "Equipo": "Team",
        "Edad": "Age",
        "Pos_Normalizada": "Position",
    }
    cols_to_show = [c for c in display_cols.keys() if c in df_ranked.columns]
    df_visible = df_ranked[cols_to_show].rename(columns=display_cols)

    st.dataframe(df_visible.head(20), width="stretch")
else:
    st.warning("Ranking columns not found. Please ensure data processing is complete.")

# 6. Navigation Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "👤 Player Profile",
    "🏆 Rankings",
    "📊 Radar Charts",
    "🔍 Advanced Search",
    "👯 Similarity",
    "📈 Z-Score",
    "🌍 Market Comparison",
    "🧩 Custom Dashboard",
    "🔄 Transfers",
    "🔬 Transfer Deep Dive",
])

# --- TAB 1: PLAYER PROFILE ---
with tab1:
    st.header("👤 Player Profile")
    with st.expander("ℹ️ How to read this card"):
        st.write("Displays general info and the Top 3 metrics where this player ranks highest.")

    temp_bio = st.radio("Season", SEASONS, key="bio_temp", horizontal=True)
    df_bio = season_df(temp_bio)

    target_bio = st.selectbox("Search Player Name:", sorted(df_bio["Jugador"].unique()), key="bio_name")

    if target_bio:
        bio = sg.get_player_bio_card(df_bio, target_bio)
        if bio:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Team", bio["Equipo"])
            c2.metric("League", bio["Liga"])
            c3.metric("Age", bio["Edad"])

            st.subheader("⭐ Standout Virtues")
            cv1, cv2, cv3 = st.columns(3)
            for i, (metrica, valor) in enumerate(bio["Top Virtudes"]):
                [cv1, cv2, cv3][i].info(f"**{metrica.replace('_Rating', '')}** \n\n {valor:.1f} / 100")

# --- TAB 2: LEAGUE RANKINGS ---
with tab2:
    st.header("🏆 League Rankings")
    with st.expander("ℹ️ About League Ranking"):
        st.write("This chart shows exactly where the player sits relative to every other player in the league that season, at their position.")

    if target_bio:
        fig_rank = sg.plot_league_rank_st(df_bio, target_bio)
        if fig_rank:
            st.pyplot(fig_rank)
            st.caption("Note: The bar represents the rating; the label shows the absolute rank position.")

# --- TAB 3: RADAR CHARTS ---
with tab3:
    st.header("📊 Multi-Player Radar Comparison")
    with st.expander("ℹ️ How to use Radar Charts"):
        st.write("Select up to 3 players (or the same player in different seasons) to visualize their rankings.")

    c1, c2, c3 = st.columns(3)
    sel_radar = []

    with c1:
        st.markdown("### 🟢 Primary Profile")
        t1 = st.radio("Season", SEASONS, key="p1_t", horizontal=True)
        df_1 = season_df(t1)
        p1 = st.selectbox("Player", sorted(df_1["Jugador"].unique()), key="p1_n")
        sel_radar.append((p1, df_1, f"{p1} ({t1})"))

    with c2:
        st.markdown("### 🔴 Secondary Profile")
        activar_p2 = st.checkbox("Add second player", key="act_p2")
        if activar_p2:
            t2 = st.radio("Season", SEASONS, key="p2_t", horizontal=True)
            df_2 = season_df(t2)
            p2 = st.selectbox("Player", sorted(df_2["Jugador"].unique()), key="p2_n")
            sel_radar.append((p2, df_2, f"{p2} ({t2})"))

    with c3:
        st.markdown("### 🔵 Comparison Profile")
        activar_p3 = st.checkbox("Add third player", key="act_p3")
        if activar_p3:
            t3 = st.radio("Season", SEASONS, key="p3_t", horizontal=True)
            df_3 = season_df(t3)
            p3 = st.selectbox("Player", sorted(df_3["Jugador"].unique()), key="p3_n")
            sel_radar.append((p3, df_3, f"{p3} ({t3})"))

    if st.button("📊 Generate Visual Radar"):
        if sel_radar:
            fig = sg.plot_omni_radar_evolutivo(sel_radar)
            if fig:
                _, col_radar, _ = st.columns([1, 5, 1])
                with col_radar:
                    st.pyplot(fig)

                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=300, bbox_inches="tight", facecolor="white")
                buf.seek(0)
                names_slug = "_vs_".join(p[0].replace(" ", "_") for p in sel_radar)
                st.download_button(
                    label="⬇️ Download Radar Chart (PNG)",
                    data=buf,
                    file_name=f"radar_{names_slug}.png",
                    mime="image/png",
                )
            else:
                first_player = sel_radar[0][0] if sel_radar else "selected player"
                st.warning(
                    f"⚠️ Could not generate radar for **{first_player}**. "
                    "Their position either has no rating config or fewer than 3 "
                    "pillars could be computed from the available data columns. "
                    "Try selecting a different position."
                )

# --- TAB 4: ADVANCED SEARCH ---
with tab4:
    st.header("🔍 Advanced Search")
    with st.expander("ℹ️ About the Search Engine"):
        st.write("Set minimum requirements. The sliders represent **Percentiles (0-100)**. A value of 80 means the player must be in the top 20% for that metric.")

    c_temp, c_pos = st.columns([1, 1])
    with c_temp:
        temp_search = st.radio("Season to Search:", SEASONS, key="search_temp", horizontal=True)
        df_search = season_df(temp_search)
    with c_pos:
        pos_options_search = sorted(df_search["Pos_Normalizada"].unique())
        pos_filter_search = st.multiselect(
            "Filter by Position:", pos_options_search, key=f"search_pos_{temp_search}"
        )

    if pos_filter_search:
        df_search = df_search[df_search["Pos_Normalizada"].isin(pos_filter_search)]

    st.markdown("---")
    # Solo mostramos sliders de pilares que realmente aplican a las posiciones
    # seleccionadas (evita sliders de pilares de portero al filtrar por CB, etc.)
    metrics_search = [
        c for c in df_search.columns
        if "_Rating" in c and df_search[c].notna().any()
    ]
    filtros_scouting = {}

    st.subheader("📊 Metric Percentile Requirements")
    col_f1, col_f2, col_f3 = st.columns(3)

    pos_key_part = "_".join(pos_filter_search) if pos_filter_search else "all"
    for i, metrica in enumerate(metrics_search):
        target_col = [col_f1, col_f2, col_f3][i % 3]
        with target_col:
            filtros_scouting[metrica] = st.slider(
                f"{metrica.replace('_Rating', '')}",
                0, 100, 0,
                key=f"search_slider_{metrica}_{temp_search}_{pos_key_part}",
            )

    st.markdown("---")
    c_edad, c_min = st.columns(2)
    with c_edad:
        max_edad_search = st.number_input("Maximum Age", value=28, step=1)
    with c_min:
        minutos_search = st.number_input("Minimum Minutes Played", value=900, step=100)

    df_res = sg.aplicar_filtros_scouting_st(df_search, filtros_scouting)

    if not df_res.empty:
        df_res = df_res[df_res["Edad"] <= max_edad_search]
        if "Minutos jugados" in df_res.columns:
            df_res = df_res[df_res["Minutos jugados"] >= minutos_search]

    st.subheader(f"✅ Results Found: {len(df_res)}")

    if not df_res.empty:
        st.markdown("### 🏆 Ranking Strategy")
        col_sort_search = st.selectbox(
            "Sort players by specific talent:",
            options=metrics_search,
            format_func=lambda x: x.replace("_Rating", ""),
            key="sort_selector_search",
        )

        cols_ver = ["Jugador", "Equipo", "Edad", "Pos_Normalizada"] + metrics_search
        df_final_view = df_res[cols_ver].sort_values(by=col_sort_search, ascending=False).head(50)
        df_final_view = df_final_view.rename(columns={
            "Jugador": "Player", "Equipo": "Team", "Edad": "Age", "Pos_Normalizada": "Position",
        })

        st.dataframe(
            df_final_view.style.background_gradient(subset=metrics_search, cmap="YlGn")
            .format({col: "{:.1f}" for col in metrics_search}),
            width="stretch",
            height=500,
        )

        csv_data = df_final_view.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Scouting Report (.csv)",
            data=csv_data,
            file_name=f"scouting_report_{temp_search.replace('/', '')}.csv",
            mime="text/csv",
            width="stretch",
        )
    else:
        st.warning("No players found with these exact requirements. Try lowering the sliders.")

# --- TAB 5: SIMILARITY ---
with tab5:
    st.header("👯‍♂️ Similarity")
    with st.expander("ℹ️ How Similarity works"):
        st.write("Calculates the cosine similarity between players. This finds players who share a similar profile regardless of age.")

    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        st.markdown("### 🎯 Benchmark Player")
        temp_origen = st.radio("Season of Profile:", SEASONS, key="sim_temp_org")
        df_org = season_df(temp_origen)
        target_sim = st.selectbox("Select Benchmark Player:", sorted(df_org["Jugador"].unique()))

        st.markdown("---")
        st.markdown("### 🔎 Search Target")
        temp_destino = st.radio("Search Twins in Season:", SEASONS, index=0, key="sim_temp_dest")
        df_dest = season_df(temp_destino)
        n_sim = st.slider("Number of Results:", 5, 15, 10)

        run_sim = st.button("🚀 Find Similar Players", width="stretch")

    with col_s2:
        if run_sim:
            if target_sim:
                with st.spinner(f"Analyzing statistical DNA for {target_sim}..."):
                    fig_sim = sg.plot_similar_players_cross_st(target_sim, df_org, df_dest, top_n=n_sim)
                    if fig_sim:
                        st.pyplot(fig_sim)
                    else:
                        st.error("Could not generate similarity chart. Check if metrics are available for this player.")
            else:
                st.warning("Please select a benchmark player first.")
        else:
            st.info("Configure the filters on the left and click the button to generate the twin analysis.")

# --- TAB 6: Z-SCORE ---
with tab6:
    st.header("📈 Z-Score Analysis")
    with st.expander("ℹ️ Understanding Z-Score"):
        st.write("Shows standard deviations from the mean. 0 is average. +1.0 is the top 16%. +2.0 is world class. It helps identify how 'unique' a player's trait is.")
    cz1, cz2 = st.columns(2)
    sel_z = []
    for i, col in enumerate([cz1, cz2]):
        with col:
            p = st.selectbox(f"Select Player {i + 1}", df_actual["Jugador"].unique(), key=f"zn{i}")
            t = st.radio(f"Player {i + 1} Season", SEASONS, key=f"zt{i}", horizontal=True)
            df_sel = season_df(t)
            sel_z.append((p, df_sel))
    if st.button("Calculate Z-Scores"):
        fig_z = sg.plot_zscore_st(sel_z)
        if fig_z:
            st.pyplot(fig_z)
        else:
            st.warning("Could not build the chart: check that each player played in the season selected next to their name.")

# --- TAB 7: MARKET ---
with tab7:
    st.header("🌍 Market Benchmarking")
    with st.expander("ℹ️ How to use the Market Plot"):
        st.write("Compares your player (Yellow Star) against others at their position in those specific metrics. It helps determine how good a player is in the combination of a number of metrics.")

    temp_market = st.radio("Database for Market Analysis:", SEASONS, key="mkt_temp_uni", horizontal=True)
    df_mkt_base = season_df(temp_market)

    st.markdown("---")
    col_m1, col_m2 = st.columns([1, 2])
    with col_m1:
        st.markdown("### ⚙️ Analysis Settings")
        target_m = st.selectbox("Analyze Prospect:", sorted(df_mkt_base["Jugador"].unique()))
        all_ratings = [c for c in df_mkt_base.columns if "_Rating" in c]
        selected_m = st.multiselect("Metrics for Y-Axis:", options=all_ratings, default=all_ratings[:3])
        st.info(f"Comparing **{target_m}** against others in the ({temp_market}) season.")

    with col_m2:
        if target_m and selected_m:
            fig_mkt = sg.plot_market_analysis_st(df_mkt_base, target_m, selected_m)
            st.pyplot(fig_mkt)

# --- TAB 8: CUSTOM DASHBOARD ---
with tab8:
    st.header("🧩 Custom Dashboard")
    st.write("Pick a player, choose which panels you want, and see everything together on one page.")

    cd_c1, cd_c2 = st.columns([1, 2])
    with cd_c1:
        temp_cd = st.radio("Season", SEASONS, key="cd_temp", horizontal=True)
        df_cd = season_df(temp_cd)
    with cd_c2:
        target_cd = st.selectbox("Player", sorted(df_cd["Jugador"].unique()), key="cd_name")

    st.markdown("#### 🧰 Choose the panels to display")
    pc1, pc2, pc3 = st.columns(3)
    show_bio = pc1.checkbox("👤 Profile card", value=True, key="cd_show_bio")
    show_rank = pc1.checkbox("🏆 League rankings", value=True, key="cd_show_rank")
    show_radar = pc2.checkbox("📊 Radar", value=True, key="cd_show_radar")
    show_market = pc2.checkbox("🌍 Market comparison", value=False, key="cd_show_market")
    show_z = pc3.checkbox("📈 Z-Score", value=False, key="cd_show_z")
    show_sim = pc3.checkbox("👯 Similar players", value=False, key="cd_show_sim")

    with st.expander("➕ Add comparison players (for Radar & Z-Score)"):
        cmp_options = [p for p in sorted(df_cd["Jugador"].unique()) if p != target_cd]
        cmp_players = st.multiselect("Compare with (same season):", cmp_options, key="cd_cmp")

    market_metrics = None
    if show_market:
        all_ratings_cd = [c for c in df_cd.columns if "_Rating" in c]
        market_metrics = st.multiselect(
            "🌍 Market metrics (Y-axis):",
            options=all_ratings_cd,
            default=all_ratings_cd[:3],
            key="cd_mkt_metrics",
        )

    st.markdown("---")

    if st.button("🧩 Build Dashboard", key="cd_build", width="stretch"):
        if not target_cd:
            st.warning("Please select a player first.")
        else:
            st.subheader(f"📋 Dashboard — {target_cd} ({temp_cd})")

            sel_cd = [(target_cd, df_cd, f"{target_cd} ({temp_cd})")]
            for p in cmp_players:
                sel_cd.append((p, df_cd, f"{p} ({temp_cd})"))

            if show_bio:
                st.markdown("### 👤 Profile Card")
                try:
                    bio = sg.get_player_bio_card(df_cd, target_cd)
                    if bio:
                        b1, b2, b3 = st.columns(3)
                        b1.metric("Team", bio["Equipo"])
                        b2.metric("League", bio["Liga"])
                        b3.metric("Age", bio["Edad"])
                        st.markdown("**⭐ Standout Virtues**")
                        v1, v2, v3 = st.columns(3)
                        for i, (metrica, valor) in enumerate(bio["Top Virtudes"]):
                            [v1, v2, v3][i].info(f"**{metrica.replace('_Rating', '')}** \n\n {valor:.1f} / 100")
                    else:
                        st.info("No profile card available for this player.")
                except Exception as e:
                    st.warning(f"Could not build profile card: {e}")
                st.markdown("---")

            if show_rank:
                st.markdown("### 🏆 League Rankings")
                try:
                    fig_rank_cd = sg.plot_league_rank_st(df_cd, target_cd)
                    if fig_rank_cd:
                        st.pyplot(fig_rank_cd)
                        st.caption("The bar is the rating; the label shows the absolute rank position.")
                    else:
                        st.info("No ranking chart available for this player.")
                except Exception as e:
                    st.warning(f"Could not build league rankings: {e}")
                st.markdown("---")

            if show_radar:
                st.markdown("### 📊 Radar")
                try:
                    fig_radar_cd = sg.plot_omni_radar_evolutivo(sel_cd)
                    if fig_radar_cd:
                        _, rc, _ = st.columns([1, 5, 1])
                        with rc:
                            st.pyplot(fig_radar_cd)
                    else:
                        st.warning(
                            "Could not generate radar (position may have no rating config "
                            "or fewer than 3 pillars, e.g. goalkeepers)."
                        )
                except Exception as e:
                    st.warning(f"Could not build radar: {e}")
                st.markdown("---")

            if show_market:
                st.markdown("### 🌍 Market Comparison")
                if market_metrics:
                    try:
                        fig_mkt_cd = sg.plot_market_analysis_st(df_cd, target_cd, market_metrics)
                        st.pyplot(fig_mkt_cd)
                    except Exception as e:
                        st.warning(f"Could not build market comparison: {e}")
                else:
                    st.info("Select at least one market metric above to show this panel.")
                st.markdown("---")

            if show_z:
                st.markdown("### 📈 Z-Score")
                try:
                    sel_z_cd = [(p, d) for (p, d, _lbl) in sel_cd]
                    fig_z_cd = sg.plot_zscore_st(sel_z_cd)
                    if fig_z_cd:
                        st.pyplot(fig_z_cd)
                    else:
                        st.info("Could not generate the z-score chart for this player.")
                except Exception as e:
                    st.warning(f"Could not build z-score chart: {e}")
                st.markdown("---")

            if show_sim:
                st.markdown("### 👯 Similar Players")
                try:
                    fig_sim_cd = sg.plot_similar_players_cross_st(target_cd, df_cd, df_cd, top_n=10)
                    if fig_sim_cd:
                        st.pyplot(fig_sim_cd)
                    else:
                        st.info("Could not generate similarity chart for this player.")
                except Exception as e:
                    st.warning(f"Could not build similarity chart: {e}")
                st.markdown("---")

# --- TAB 9: TRANSFERS ---
with tab9:
    st.header("🔄 Transfers")
    if league != "Eredivisie":
        st.info("This tab always covers arrivals at **Eredivisie** clubs, whichever league is selected in the sidebar.")
    with st.expander("ℹ️ About this list", expanded=True):
        st.write("""
        Every arrival at an Eredivisie club across the 4 seasons in this dashboard, scraped from
        Transfermarkt: **fee actually paid**, the club they came from, and the season they joined.
        Matched by name to the Wyscout data so you get their position too.

        This is a **plain factual list, with no automated "good signing / bad signing" verdict** —
        an early version of this tab tried to score that off Final_Score, but Final_Score blends every
        pillar for a position into one number, and that flattens real differences in player profile
        (e.g. a poacher CF and a false-9 CF who creates for others get judged on the same axes). That's
        not reliable enough to label a transfer as a bargain or a bust, so it's gone — filter and sort
        the table yourself below.

        Only **523 of the 1277 scraped arrivals** could be confidently matched to a Wyscout player who
        reached 900+ minutes in that club that season (backups, injury-hit signings and players who
        never nailed down a starting spot don't clear that bar, so they're correctly excluded — this
        isn't a matching failure).
        """)

    rep_all = st.session_state.df_transfers
    if rep_all.empty:
        st.warning("No transfer_report.parquet found. Run scrape_transfers.py + build_transfer_report.py first.")
    else:
        c_t1, c_t2, c_t3, c_t4 = st.columns(4)
        with c_t1:
            season_filter_t = st.multiselect("Season signed:", SEASONS_ERE, key="t_season")
        with c_t2:
            club_filter_t = st.multiselect(
                "Club:", sorted(rep_all["Club_destino"].unique()), key="t_club"
            )
        with c_t3:
            pos_filter_t = st.multiselect(
                "Position:", sorted(rep_all["Posicion"].dropna().unique()), key="t_pos"
            )
        with c_t4:
            fee_types_t = st.multiselect(
                "Fee type:", sorted(rep_all["Fee_tipo"].unique()),
                default=["fee", "loan_fee"], key="t_feetype"
            )

        d_t = rep_all.copy()
        if season_filter_t:
            d_t = d_t[d_t["Temporada_fichaje"].isin(season_filter_t)]
        if club_filter_t:
            d_t = d_t[d_t["Club_destino"].isin(club_filter_t)]
        if pos_filter_t:
            d_t = d_t[d_t["Posicion"].isin(pos_filter_t)]
        if fee_types_t:
            d_t = d_t[d_t["Fee_tipo"].isin(fee_types_t)]

        st.subheader(f"📋 {len(d_t)} transfers")

        show_cols_t = ["Jugador", "Posicion", "Club_destino", "Temporada_fichaje",
                        "Procedencia", "Liga_procedencia", "Fee_EUR", "Fee_tipo"]
        rename_t = {
            "Jugador": "Player",
            "Posicion": "Position",
            "Club_destino": "Club",
            "Temporada_fichaje": "Season Signed",
            "Procedencia": "From",
            "Liga_procedencia": "From League",
            "Fee_EUR": "Fee (€)",
            "Fee_tipo": "Fee Type",
        }
        d_t_view = d_t[show_cols_t].sort_values("Fee_EUR", ascending=False, na_position="last").rename(columns=rename_t)
        st.dataframe(d_t_view, width="stretch", height=550)

        csv_t = d_t_view.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download this list (.csv)", data=csv_t,
            file_name="eredivisie_transfers.csv", mime="text/csv",
        )

# --- TAB 10: TRANSFER DEEP DIVE ---
with tab10:
    st.header("🔬 Transfer Deep Dive")
    if league != "Eredivisie":
        st.info("This tab always covers transfers to **Eredivisie** clubs, whichever league is selected in the sidebar.")
    with st.expander("ℹ️ What this tab can and can't tell you", expanded=True):
        st.write("""
        Two independent signals, picked apart on purpose instead of blended into one score:

        - **Market value over time** (Transfermarkt) — works for *any* transfer, wherever the player
          played. It tells you **whether** the market thinks a move worked (value rose or fell), but
          not **why** — it's reputation/output as judged by the market, not our own stats.
        - **Pillar-by-pillar before/after** — only possible for the **158 transfers between two
          Eredivisie clubs**, where we have real Wyscout data on both sides. This is the one that can
          answer **why**: which specific qualities got better or worse, not one blended number. Even
          within this group, about a third joined in 22/23 (the first season in this dataset, so there's
          no "before") or didn't clear 900 minutes the year before — for those you'll only see the
          "after" side.

        For a transfer involving a foreign club, there is no stats-based "why" here — that would need
        Wyscout data for that league/season, which this dashboard doesn't have.
        """)

    rep_dd = st.session_state.df_transfers
    if rep_dd.empty:
        st.warning("No transfer_report.parquet found.")
    else:
        rep_dd = rep_dd.dropna(subset=["player_id"]).copy()
        rep_dd["label"] = (
            rep_dd["Jugador"] + "  —  " + rep_dd["Procedencia"] + " → " + rep_dd["Club_destino"]
            + " (" + rep_dd["Temporada_fichaje"] + ")"
        )
        rep_dd = rep_dd.sort_values(["is_domestic", "Temporada_fichaje"], ascending=[False, False])

        c_dd1, c_dd2 = st.columns([1, 1])
        with c_dd1:
            only_domestic_dd = st.checkbox("Show only Eredivisie-internal transfers (has real before/after)", value=True)
        pool_dd = rep_dd[rep_dd["is_domestic"]] if only_domestic_dd else rep_dd

        selected_label = st.selectbox("Pick a transfer:", pool_dd["label"].tolist())
        row_dd = pool_dd[pool_dd["label"] == selected_label].iloc[0]

        c_info1, c_info2, c_info3, c_info4 = st.columns(4)
        c_info1.metric("Position", row_dd["Posicion"])
        c_info2.metric("Fee", f"€{row_dd['Fee_EUR']/1e6:.2f}M" if pd.notna(row_dd["Fee_EUR"]) else row_dd["Fee_tipo"])
        c_info3.metric("From", row_dd["Procedencia"])
        c_info4.metric("Signed", row_dd["Temporada_fichaje"])

        st.markdown("---")
        st.subheader("📈 Market value over time")
        history = st.session_state.market_values.get(str(row_dd["player_id"]), [])
        transfer_date = None
        if row_dd["Temporada_fichaje"] in SEASONS_ERE:
            year = 2000 + int(row_dd["Temporada_fichaje"].split("/")[0])
            transfer_date = pd.Timestamp(year=year, month=7, day=1)
        fig_mv = sg.plot_market_value_trend(
            history, transfer_date=transfer_date, transfer_fee=row_dd["Fee_EUR"], player_name=row_dd["Jugador"]
        )
        if fig_mv:
            st.pyplot(fig_mv)
        else:
            st.info("No market value history available for this player.")

        st.markdown("---")
        st.subheader("🔍 Pillar-by-pillar: before vs after")
        if not row_dd["is_domestic"]:
            st.info(
                "This player arrived from outside the Eredivisie (or from a club we couldn't match), "
                "so there's no prior-season Wyscout data here to compare against — no stats-based "
                "'why' is possible for this one."
            )
        else:
            before_row, after_row, prev_season = sg.get_transfer_before_after(
                st.session_state.df_all[st.session_state.df_all["Liga"] == "Eredivisie"], row_dd["Jugador"], row_dd["Procedencia_Wyscout"],
                row_dd["Club_destino"], row_dd["Temporada_fichaje"],
            )
            if before_row is None:
                reason = (
                    f"they signed in {row_dd['Temporada_fichaje']}, the first season in this dataset"
                    if prev_season is None else
                    f"they didn't reach 900 minutes at {row_dd['Procedencia_Wyscout']} in {prev_season}"
                )
                st.info(f"No 'before' season available ({reason}).")
            elif after_row is None:
                st.info(f"No 'after' season available for {row_dd['Jugador']} at {row_dd['Club_destino']} yet.")
            else:
                fig_pillar = sg.plot_transfer_pillar_comparison(before_row, after_row)
                if fig_pillar:
                    st.pyplot(fig_pillar)
                    st.caption(
                        "Each pillar is its own percentile within position & season — nothing blended "
                        "into a single score, so you can see exactly which qualities moved and which didn't."
                    )
                else:
                    st.info("Not enough shared pillars between the two seasons to compare (likely a position change).")
