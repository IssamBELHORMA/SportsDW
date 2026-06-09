import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SportsDW — La Liga",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = Path(__file__).parent.parent / "warehouse.ddb"

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Base */
    [data-testid="stAppViewContainer"] { background: #0e0e0e; }
    [data-testid="stSidebar"] { background: #161616; border-right: 1px solid #2a2a2a; }

    /* Typography */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #e0e0e0; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 8px;
        padding: 16px;
    }
    [data-testid="metric-container"] label { color: #888 !important; font-size: 0.75rem !important; letter-spacing: 0.08em; text-transform: uppercase; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #e8ff47 !important; font-size: 1.8rem !important; font-weight: 700; }
    [data-testid="metric-container"] [data-testid="stMetricDelta"] { color: #aaa !important; }

    /* Section headers */
    .section-label {
        font-size: 0.7rem;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: #e8ff47;
        margin-bottom: 4px;
        font-weight: 600;
    }
    .page-title {
        font-size: 2rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.02em;
        margin-bottom: 2px;
    }
    .page-sub {
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 24px;
    }

    /* Divider */
    hr { border-color: #2a2a2a !important; margin: 24px 0; }

    /* Table */
    [data-testid="stDataFrame"] { border: 1px solid #2a2a2a; border-radius: 8px; }

    /* Selectbox / sidebar widgets */
    .stSelectbox label, .stMultiSelect label { color: #888 !important; font-size: 0.75rem !important; letter-spacing: 0.08em; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

PLOT_THEME = dict(
    paper_bgcolor="#0e0e0e",
    plot_bgcolor="#141414",
    font_color="#aaa",
    font_family="Inter",
    margin=dict(l=16, r=16, t=36, b=16),
    colorway=["#e8ff47", "#4fc3f7", "#ff6e6e", "#b39ddb", "#80cbc4"],
)

# ── DB helpers ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_conn():
    return duckdb.connect(str(DB_PATH), read_only=True)

@st.cache_data
def query(sql: str) -> pd.DataFrame:
    return get_conn().execute(sql).fetchdf()

@st.cache_data
def get_seasons():
    return query("SELECT season_label FROM gold.dim_season ORDER BY season_label")["season_label"].tolist()

@st.cache_data
def get_teams():
    return query("SELECT team_name FROM gold.dim_team ORDER BY team_name")["team_name"].tolist()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚽ SportsDW")
    st.markdown("<div style='color:#555;font-size:0.8rem;margin-bottom:24px'>La Liga · 2022–2026</div>", unsafe_allow_html=True)
    page = st.radio(
        "VIEW",
        ["League Overview", "Team Deep-Dive", "Head to Head"],
        label_visibility="visible",
    )
    st.markdown("---")
    st.markdown("<div style='color:#444;font-size:0.7rem'>Built with DuckDB + dbt</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — League Overview
# ══════════════════════════════════════════════════════════════════════════════
if page == "League Overview":
    st.markdown("<div class='page-title'>League Overview</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Season-by-season summary across all La Liga campaigns</div>", unsafe_allow_html=True)

    df = query("""
        SELECT
            s.season_label,
            COUNT(f.match_id)                                                   AS matches,
            SUM(f.home_goals + f.away_goals)                                    AS total_goals,
            ROUND(AVG(f.home_goals + f.away_goals), 2)                          AS avg_goals,
            SUM(CASE WHEN f.result = 'H' THEN 1 ELSE 0 END)                    AS home_wins,
            SUM(CASE WHEN f.result = 'D' THEN 1 ELSE 0 END)                    AS draws,
            SUM(CASE WHEN f.result = 'A' THEN 1 ELSE 0 END)                    AS away_wins,
            ROUND(100.0 * SUM(CASE WHEN f.result = 'H' THEN 1 ELSE 0 END)
                  / COUNT(*), 1)                                                AS home_win_pct,
            SUM(f.home_yellow_cards + f.away_yellow_cards)                      AS yellow_cards,
            SUM(f.home_red_cards + f.away_red_cards)                            AS red_cards
        FROM gold.fact_matches f
        JOIN gold.dim_season s ON f.season_id = s.season_id
        GROUP BY s.season_label
        ORDER BY s.season_label
    """)

    # KPI row — latest season
    latest = df.iloc[-1]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Season", latest["season_label"])
    c2.metric("Total Goals", int(latest["total_goals"]))
    c3.metric("Avg Goals / Match", latest["avg_goals"])
    c4.metric("Home Win %", f"{latest['home_win_pct']}%")
    c5.metric("Red Cards", int(latest["red_cards"]))

    st.markdown("---")

    # Goals trend
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='section-label'>Total Goals per Season</div>", unsafe_allow_html=True)
        fig = px.bar(df, x="season_label", y="total_goals", text="total_goals",
                     color_discrete_sequence=["#e8ff47"])
        fig.update_traces(textposition="outside", textfont_color="#aaa")
        fig.update_layout(**PLOT_THEME, xaxis_title="", yaxis_title="Goals",
                          xaxis=dict(tickfont_color="#666"), yaxis=dict(tickfont_color="#666",
                          gridcolor="#1e1e1e"))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("<div class='section-label'>Avg Goals per Match</div>", unsafe_allow_html=True)
        fig = px.line(df, x="season_label", y="avg_goals", markers=True,
                      color_discrete_sequence=["#4fc3f7"])
        fig.update_traces(line_width=2.5, marker_size=8)
        fig.update_layout(**PLOT_THEME, xaxis_title="", yaxis_title="Avg Goals",
                          xaxis=dict(tickfont_color="#666"), yaxis=dict(tickfont_color="#666",
                          gridcolor="#1e1e1e"))
        st.plotly_chart(fig, use_container_width=True)

    # Result distribution
    st.markdown("<div class='section-label'>Result Distribution per Season</div>", unsafe_allow_html=True)
    result_df = df[["season_label", "home_wins", "draws", "away_wins"]].melt(
        id_vars="season_label", var_name="result", value_name="count"
    )
    result_df["result"] = result_df["result"].map({
        "home_wins": "Home Win", "draws": "Draw", "away_wins": "Away Win"
    })
    fig = px.bar(result_df, x="season_label", y="count", color="result", barmode="group",
                 color_discrete_map={"Home Win": "#e8ff47", "Draw": "#4fc3f7", "Away Win": "#ff6e6e"})
    fig.update_layout(**PLOT_THEME, xaxis_title="", yaxis_title="Matches",
                      legend_title="", xaxis=dict(tickfont_color="#666"),
                      yaxis=dict(tickfont_color="#666", gridcolor="#1e1e1e"))
    st.plotly_chart(fig, use_container_width=True)

    # Full table
    st.markdown("<div class='section-label'>Full Season Table</div>", unsafe_allow_html=True)
    st.dataframe(df.rename(columns={
        "season_label": "Season", "matches": "Matches", "total_goals": "Goals",
        "avg_goals": "Avg/Match", "home_wins": "Home W", "draws": "Draws",
        "away_wins": "Away W", "home_win_pct": "Home W%",
        "yellow_cards": "Yellows", "red_cards": "Reds"
    }), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Team Deep-Dive
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Team Deep-Dive":
    st.markdown("<div class='page-title'>Team Deep-Dive</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Select a team and season to explore their campaign</div>", unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 1])
    with col_a:
        selected_team = st.selectbox("TEAM", get_teams())
    with col_b:
        season_options = ["All Seasons"] + get_seasons()
        selected_season = st.selectbox("SEASON", season_options)

    season_filter = "" if selected_season == "All Seasons" else f"AND s.season_label = '{selected_season}'"

    # Per-match results for the team
    matches_df = query(f"""
        SELECT
            s.season_label                                                          AS season,
            d.full_date                                                             AS date,
            CASE WHEN f.team_id_home = t.team_id THEN 'Home' ELSE 'Away' END       AS venue,
            CASE WHEN f.team_id_home = t.team_id
                 THEN ht.team_name ELSE at2.team_name END                           AS opponent,
            CASE WHEN f.team_id_home = t.team_id
                 THEN f.home_goals ELSE f.away_goals END                            AS gf,
            CASE WHEN f.team_id_home = t.team_id
                 THEN f.away_goals ELSE f.home_goals END                            AS ga,
            CASE WHEN (f.team_id_home = t.team_id AND f.result = 'H')
                   OR (f.team_id_away = t.team_id AND f.result = 'A') THEN 'W'
                 WHEN f.result = 'D' THEN 'D'
                 ELSE 'L' END                                                       AS result,
            CASE WHEN f.team_id_home = t.team_id
                 THEN f.home_shots_on_target ELSE f.away_shots_on_target END        AS shots_on_target,
            CASE WHEN f.team_id_home = t.team_id
                 THEN f.home_yellow_cards ELSE f.away_yellow_cards END              AS yellows
        FROM gold.fact_matches f
        JOIN gold.dim_team   t   ON t.team_name = '{selected_team}'
        JOIN gold.dim_team   ht  ON f.team_id_home = ht.team_id
        JOIN gold.dim_team   at2 ON f.team_id_away = at2.team_id
        JOIN gold.dim_season s   ON f.season_id = s.season_id
        JOIN gold.dim_date   d   ON f.date_id = d.date_id
        WHERE t.team_id IN (f.team_id_home, f.team_id_away)
        {season_filter}
        ORDER BY d.full_date
    """)

    if matches_df.empty:
        st.warning("No data found for this selection.")
        st.stop()

    # KPIs
    wins   = (matches_df["result"] == "W").sum()
    draws  = (matches_df["result"] == "D").sum()
    losses = (matches_df["result"] == "L").sum()
    total  = len(matches_df)
    gf     = matches_df["gf"].sum()
    ga     = matches_df["ga"].sum()

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Matches", total)
    k2.metric("Wins", int(wins))
    k3.metric("Draws", int(draws))
    k4.metric("Losses", int(losses))
    k5.metric("Goals For", int(gf))
    k6.metric("Goal Diff", f"{int(gf - ga):+d}")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        # Win/Draw/Loss donut
        st.markdown("<div class='section-label'>Result Breakdown</div>", unsafe_allow_html=True)
        pie_df = pd.DataFrame({
            "Result": ["Win", "Draw", "Loss"],
            "Count":  [wins, draws, losses]
        })
        fig = px.pie(pie_df, names="Result", values="Count", hole=0.55,
                     color="Result",
                     color_discrete_map={"Win": "#e8ff47", "Draw": "#4fc3f7", "Loss": "#ff6e6e"})
        fig.update_layout(**PLOT_THEME, showlegend=True,
                          legend=dict(font_color="#aaa", bgcolor="rgba(0,0,0,0)"))
        fig.update_traces(textfont_color="#111", textfont_size=12)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Goals scored vs conceded by season
        st.markdown("<div class='section-label'>Goals For vs Against by Season</div>", unsafe_allow_html=True)
        season_goals = matches_df.groupby("season").agg(
            goals_for=("gf", "sum"),
            goals_against=("ga", "sum")
        ).reset_index()
        fig = go.Figure()
        fig.add_bar(x=season_goals["season"], y=season_goals["goals_for"],
                    name="Goals For", marker_color="#e8ff47")
        fig.add_bar(x=season_goals["season"], y=season_goals["goals_against"],
                    name="Goals Against", marker_color="#ff6e6e")
        fig.update_layout(**PLOT_THEME, barmode="group", xaxis_title="",
                          yaxis_title="Goals", legend=dict(font_color="#aaa",
                          bgcolor="rgba(0,0,0,0)"),
                          xaxis=dict(tickfont_color="#666"),
                          yaxis=dict(tickfont_color="#666", gridcolor="#1e1e1e"))
        st.plotly_chart(fig, use_container_width=True)

    # Home vs Away win rate
    st.markdown("<div class='section-label'>Home vs Away Performance</div>", unsafe_allow_html=True)
    venue_df = matches_df.groupby("venue").apply(
        lambda x: pd.Series({
            "Matches": len(x),
            "Wins":    (x["result"] == "W").sum(),
            "Draws":   (x["result"] == "D").sum(),
            "Losses":  (x["result"] == "L").sum(),
            "Goals For": x["gf"].sum(),
            "Goals Against": x["ga"].sum(),
        })
    ).reset_index()
    venue_df["Win %"] = (venue_df["Wins"] / venue_df["Matches"] * 100).round(1)
    st.dataframe(venue_df, use_container_width=True, hide_index=True)

    # Match log
    st.markdown("<div class='section-label'>Match Log</div>", unsafe_allow_html=True)
    display_df = matches_df[["date", "season", "venue", "opponent", "gf", "ga", "result", "shots_on_target", "yellows"]].copy()
    display_df.columns = ["Date", "Season", "Venue", "Opponent", "GF", "GA", "Result", "Shots OT", "Yellows"]

    def color_result(val):
        colors = {"W": "color:#e8ff47;font-weight:700",
                  "D": "color:#4fc3f7",
                  "L": "color:#ff6e6e"}
        return colors.get(val, "")

    st.dataframe(display_df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Head to Head
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Head to Head":
    st.markdown("<div class='page-title'>Head to Head</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Compare two teams across all their meetings</div>", unsafe_allow_html=True)

    teams = get_teams()
    col_a, col_b, col_c = st.columns([2, 2, 1])
    with col_a:
        team_a = st.selectbox("TEAM A", teams, index=teams.index("Barcelona") if "Barcelona" in teams else 0)
    with col_b:
        team_b = st.selectbox("TEAM B", [t for t in teams if t != team_a],
                               index=0 if teams[0] != team_a else 1)
    with col_c:
        season_options = ["All Seasons"] + get_seasons()
        h2h_season = st.selectbox("SEASON", season_options)

    season_filter = "" if h2h_season == "All Seasons" else f"AND s.season_label = '{h2h_season}'"

    h2h_df = query(f"""
        SELECT
            s.season_label                                          AS season,
            d.full_date                                             AS date,
            ht.team_name                                            AS home_team,
            at2.team_name                                           AS away_team,
            f.home_goals                                            AS home_goals,
            f.away_goals                                            AS away_goals,
            f.result,
            f.home_shots_on_target,
            f.away_shots_on_target,
            f.home_corners,
            f.away_corners,
            f.home_yellow_cards,
            f.away_yellow_cards
        FROM gold.fact_matches f
        JOIN gold.dim_team   ht  ON f.team_id_home = ht.team_id
        JOIN gold.dim_team   at2 ON f.team_id_away = at2.team_id
        JOIN gold.dim_season s   ON f.season_id = s.season_id
        JOIN gold.dim_date   d   ON f.date_id = d.date_id
        WHERE (ht.team_name = '{team_a}' AND at2.team_name = '{team_b}')
           OR (ht.team_name = '{team_b}' AND at2.team_name = '{team_a}')
        {season_filter}
        ORDER BY d.full_date
    """)

    if h2h_df.empty:
        st.info(f"No matches found between {team_a} and {team_b} for this selection.")
        st.stop()

    # Compute per-team wins
    def team_result(row, team):
        if row["home_team"] == team:
            if row["result"] == "H": return "W"
            if row["result"] == "D": return "D"
            return "L"
        else:
            if row["result"] == "A": return "W"
            if row["result"] == "D": return "D"
            return "L"

    h2h_df["result_a"] = h2h_df.apply(team_result, axis=1, team=team_a)
    wins_a  = (h2h_df["result_a"] == "W").sum()
    draws   = (h2h_df["result_a"] == "D").sum()
    wins_b  = (h2h_df["result_a"] == "L").sum()
    total   = len(h2h_df)

    # Goals
    goals_a = h2h_df.apply(lambda r: r["home_goals"] if r["home_team"] == team_a else r["away_goals"], axis=1).sum()
    goals_b = h2h_df.apply(lambda r: r["home_goals"] if r["home_team"] == team_b else r["away_goals"], axis=1).sum()

    # KPI banner
    st.markdown(f"""
    <div style='display:flex;align-items:center;justify-content:center;gap:32px;
                background:#1a1a1a;border:1px solid #2a2a2a;border-radius:12px;
                padding:24px;margin:16px 0'>
        <div style='text-align:center'>
            <div style='font-size:2.4rem;font-weight:800;color:#e8ff47'>{team_a}</div>
            <div style='font-size:3rem;font-weight:900;color:#fff'>{wins_a}</div>
            <div style='color:#555;font-size:0.75rem;letter-spacing:0.1em'>WINS</div>
        </div>
        <div style='text-align:center'>
            <div style='font-size:1rem;color:#555;letter-spacing:0.1em'>DRAWS</div>
            <div style='font-size:2.4rem;font-weight:800;color:#4fc3f7'>{draws}</div>
            <div style='color:#555;font-size:0.75rem'>{total} meetings</div>
        </div>
        <div style='text-align:center'>
            <div style='font-size:2.4rem;font-weight:800;color:#ff6e6e'>{team_b}</div>
            <div style='font-size:3rem;font-weight:900;color:#fff'>{wins_b}</div>
            <div style='color:#555;font-size:0.75rem;letter-spacing:0.1em'>WINS</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        # Goals comparison
        st.markdown("<div class='section-label'>Goals Scored</div>", unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_bar(x=[team_a], y=[int(goals_a)], name=team_a,
                    marker_color="#e8ff47", text=[int(goals_a)], textposition="outside")
        fig.add_bar(x=[team_b], y=[int(goals_b)], name=team_b,
                    marker_color="#ff6e6e", text=[int(goals_b)], textposition="outside")
        fig.update_layout(**PLOT_THEME, showlegend=False, yaxis_title="Total Goals",
                          xaxis=dict(tickfont_color="#aaa", tickfont_size=13),
                          yaxis=dict(tickfont_color="#666", gridcolor="#1e1e1e"))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Win share donut
        st.markdown("<div class='section-label'>Win Share</div>", unsafe_allow_html=True)
        pie_df = pd.DataFrame({
            "Team":  [team_a, "Draw", team_b],
            "Count": [wins_a, draws, wins_b]
        })
        fig = px.pie(pie_df, names="Team", values="Count", hole=0.55,
                     color="Team",
                     color_discrete_map={team_a: "#e8ff47", "Draw": "#4fc3f7", team_b: "#ff6e6e"})
        fig.update_layout(**PLOT_THEME, legend=dict(font_color="#aaa", bgcolor="rgba(0,0,0,0)"))
        fig.update_traces(textfont_color="#111", textfont_size=12)
        st.plotly_chart(fig, use_container_width=True)

    # Stats radar
    st.markdown("<div class='section-label'>Average Match Stats</div>", unsafe_allow_html=True)

    avg_sot_a = h2h_df.apply(lambda r: r["home_shots_on_target"] if r["home_team"] == team_a
                              else r["away_shots_on_target"], axis=1).mean()
    avg_sot_b = h2h_df.apply(lambda r: r["home_shots_on_target"] if r["home_team"] == team_b
                              else r["away_shots_on_target"], axis=1).mean()
    avg_cor_a = h2h_df.apply(lambda r: r["home_corners"] if r["home_team"] == team_a
                              else r["away_corners"], axis=1).mean()
    avg_cor_b = h2h_df.apply(lambda r: r["home_corners"] if r["home_team"] == team_b
                              else r["away_corners"], axis=1).mean()
    avg_yel_a = h2h_df.apply(lambda r: r["home_yellow_cards"] if r["home_team"] == team_a
                              else r["away_yellow_cards"], axis=1).mean()
    avg_yel_b = h2h_df.apply(lambda r: r["home_yellow_cards"] if r["home_team"] == team_b
                              else r["away_yellow_cards"], axis=1).mean()
    avg_gf_a  = goals_a / total
    avg_gf_b  = goals_b / total

    categories = ["Goals/Match", "Shots on Target", "Corners", "Yellow Cards"]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[round(avg_gf_a, 2), round(avg_sot_a, 2), round(avg_cor_a, 2), round(avg_yel_a, 2)],
        theta=categories, fill="toself", name=team_a,
        line_color="#e8ff47", fillcolor="rgba(232,255,71,0.15)"
    ))
    fig.add_trace(go.Scatterpolar(
        r=[round(avg_gf_b, 2), round(avg_sot_b, 2), round(avg_cor_b, 2), round(avg_yel_b, 2)],
        theta=categories, fill="toself", name=team_b,
        line_color="#ff6e6e", fillcolor="rgba(255,110,110,0.15)"
    ))
    fig.update_layout(
        **PLOT_THEME,
        polar=dict(
            bgcolor="#FFFDFD",
            radialaxis=dict(visible=True, color="#333", gridcolor="#222"),
            angularaxis=dict(color="#666")
        ),
        legend=dict(font_color="#aaa", bgcolor="rgba(0,0,0,0)"),
        height=380
    )
    st.plotly_chart(fig, use_container_width=True)

    # Match history table
    st.markdown("<div class='section-label'>Match History</div>", unsafe_allow_html=True)
    display = h2h_df[["date", "season", "home_team", "home_goals", "away_goals", "away_team"]].copy()
    display.columns = ["Date", "Season", "Home", "HG", "AG", "Away"]
    st.dataframe(display, use_container_width=True, hide_index=True)