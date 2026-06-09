import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SportsDW — La Liga",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = Path(__file__).parent.parent / "warehouse.ddb"

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        color: #111111;
    }
    [data-testid="stAppViewContainer"] { background: #ffffff; }
    [data-testid="stSidebar"] { background: #f7f7f5; border-right: 1px solid #e8e8e4; }

    [data-testid="metric-container"] {
        background: #f7f7f5;
        border: 1px solid #e8e8e4;
        border-radius: 10px;
        padding: 18px 20px;
    }
    [data-testid="metric-container"] label {
        color: #888 !important;
        font-size: 0.7rem !important;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        font-family: 'DM Mono', monospace !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #111 !important;
        font-size: 1.9rem !important;
        font-weight: 700;
    }

    .page-title {
        font-size: 2rem; font-weight: 700; color: #111;
        letter-spacing: -0.03em; margin-bottom: 2px;
    }
    .page-sub { font-size: 0.9rem; color: #999; margin-bottom: 20px; }
    .section-label {
        font-family: 'DM Mono', monospace;
        font-size: 0.65rem; letter-spacing: 0.12em;
        text-transform: uppercase; color: #aaa; margin-bottom: 6px;
    }
    .brand { font-size: 1.1rem; font-weight: 700; color: #111; letter-spacing: -0.02em; }
    .brand-sub {
        font-family: 'DM Mono', monospace; font-size: 0.65rem;
        color: #aaa; letter-spacing: 0.08em; margin-bottom: 28px;
    }
    .h2h-banner {
        display: flex; align-items: center; justify-content: center; gap: 48px;
        background: #f7f7f5; border: 1px solid #e8e8e4;
        border-radius: 12px; padding: 28px 24px; margin: 16px 0;
    }
    hr { border-color: #e8e8e4 !important; margin: 20px 0; }
    [data-testid="stDataFrame"] { border: 1px solid #e8e8e4; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

PLOT_THEME = dict(
    paper_bgcolor="#ffffff", plot_bgcolor="#fafaf8",
    font_color="#444", font_family="DM Sans",
    margin=dict(l=16, r=16, t=36, b=16),
    colorway=["#2563eb", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6"],
)
ACCENT   = "#2563eb"
ACCENT_B = "#ef4444"
NEUTRAL  = "#f59e0b"
GRID     = "#eeeeea"

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

# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div class='brand'>⚽ SportsDW</div>", unsafe_allow_html=True)
    st.markdown("<div class='brand-sub'>LA LIGA · 2022–2026</div>", unsafe_allow_html=True)
    page = st.radio("VIEW", ["League Overview", "Team Deep-Dive", "Head to Head"])
    st.markdown("---")
    st.markdown("<div style='font-family:DM Mono,monospace;font-size:0.65rem;color:#ccc;letter-spacing:0.06em'>DuckDB · dbt · Streamlit</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — League Overview
# ══════════════════════════════════════════════════════════════════════════════
if page == "League Overview":
    st.markdown("<div class='page-title'>League Overview</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Season-by-season summary across all La Liga campaigns</div>", unsafe_allow_html=True)

    df = query("""
        SELECT
            s.season_label,
            COUNT(f.match_id)                                                AS matches,
            SUM(f.home_goals + f.away_goals)                                 AS total_goals,
            ROUND(AVG(f.home_goals + f.away_goals), 2)                       AS avg_goals,
            SUM(CASE WHEN f.result = 'H' THEN 1 ELSE 0 END)                 AS home_wins,
            SUM(CASE WHEN f.result = 'D' THEN 1 ELSE 0 END)                 AS draws,
            SUM(CASE WHEN f.result = 'A' THEN 1 ELSE 0 END)                 AS away_wins,
            ROUND(100.0 * SUM(CASE WHEN f.result = 'H' THEN 1 ELSE 0 END)
                  / COUNT(*), 1)                                             AS home_win_pct,
            SUM(f.home_yellow_cards + f.away_yellow_cards)                   AS yellow_cards,
            SUM(f.home_red_cards   + f.away_red_cards)                       AS red_cards
        FROM gold.fact_matches f
        JOIN gold.dim_season s ON f.season_id = s.season_id
        GROUP BY s.season_label
        ORDER BY s.season_label
    """)

    latest = df.iloc[-1]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Latest Season",     latest["season_label"])
    c2.metric("Total Goals",       int(latest["total_goals"]))
    c3.metric("Avg Goals / Match", latest["avg_goals"])
    c4.metric("Home Win %",        f"{latest['home_win_pct']}%")
    c5.metric("Red Cards",         int(latest["red_cards"]))

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='section-label'>Total Goals per Season</div>", unsafe_allow_html=True)
        fig = px.bar(df, x="season_label", y="total_goals", text="total_goals",
                     color_discrete_sequence=[ACCENT])
        fig.update_traces(textposition="outside", textfont_color="#666", marker_line_width=0)
        fig.update_layout(**PLOT_THEME, xaxis_title="", yaxis_title="Goals",
                          xaxis=dict(tickfont_color="#888"),
                          yaxis=dict(tickfont_color="#888", gridcolor=GRID))
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.markdown("<div class='section-label'>Avg Goals per Match</div>", unsafe_allow_html=True)
        fig = px.line(df, x="season_label", y="avg_goals", markers=True,
                      color_discrete_sequence=[NEUTRAL])
        fig.update_traces(line_width=2.5, marker_size=9,
                          marker_color=NEUTRAL, marker_line_color="#fff", marker_line_width=2)
        fig.update_layout(**PLOT_THEME, xaxis_title="", yaxis_title="Avg Goals",
                          xaxis=dict(tickfont_color="#888"),
                          yaxis=dict(tickfont_color="#888", gridcolor=GRID))
        st.plotly_chart(fig, width='stretch')

    st.markdown("<div class='section-label'>Result Distribution per Season</div>", unsafe_allow_html=True)
    result_df = df[["season_label", "home_wins", "draws", "away_wins"]].melt(
        id_vars="season_label", var_name="result", value_name="count"
    )
    result_df["result"] = result_df["result"].map(
        {"home_wins": "Home Win", "draws": "Draw", "away_wins": "Away Win"}
    )
    fig = px.bar(result_df, x="season_label", y="count", color="result", barmode="group",
                 color_discrete_map={"Home Win": ACCENT, "Draw": NEUTRAL, "Away Win": ACCENT_B})
    fig.update_layout(**PLOT_THEME, xaxis_title="", yaxis_title="Matches",
                      legend_title="", xaxis=dict(tickfont_color="#888"),
                      yaxis=dict(tickfont_color="#888", gridcolor=GRID),
                      legend=dict(bgcolor="rgba(0,0,0,0)"))
    st.plotly_chart(fig, width='stretch')

    st.markdown("<div class='section-label'>Full Season Table</div>", unsafe_allow_html=True)
    st.dataframe(df.rename(columns={
        "season_label": "Season", "matches": "Matches", "total_goals": "Goals",
        "avg_goals": "Avg/Match", "home_wins": "Home W", "draws": "Draws",
        "away_wins": "Away W", "home_win_pct": "Home W%",
        "yellow_cards": "Yellows", "red_cards": "Reds"
    }), width='stretch', hide_index=True)


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

    matches_df = query(f"""
        SELECT
            s.season_label                                                         AS season,
            d.full_date                                                            AS date,
            CASE WHEN f.team_id_home = t.team_id THEN 'Home' ELSE 'Away' END      AS venue,
            CASE WHEN f.team_id_home = t.team_id
                 THEN at2.team_name ELSE ht.team_name END                          AS opponent,
            CASE WHEN f.team_id_home = t.team_id
                 THEN f.home_goals ELSE f.away_goals END                           AS gf,
            CASE WHEN f.team_id_home = t.team_id
                 THEN f.away_goals ELSE f.home_goals END                           AS ga,
            CASE WHEN (f.team_id_home = t.team_id AND f.result = 'H')
                   OR (f.team_id_away = t.team_id AND f.result = 'A') THEN 'W'
                 WHEN f.result = 'D' THEN 'D'
                 ELSE 'L' END                                                      AS result,
            CASE WHEN f.team_id_home = t.team_id
                 THEN f.home_shots_on_target ELSE f.away_shots_on_target END       AS shots_on_target,
            CASE WHEN f.team_id_home = t.team_id
                 THEN f.home_yellow_cards ELSE f.away_yellow_cards END             AS yellows
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

    wins   = (matches_df["result"] == "W").sum()
    draws  = (matches_df["result"] == "D").sum()
    losses = (matches_df["result"] == "L").sum()
    total  = len(matches_df)
    gf     = int(matches_df["gf"].sum())
    ga     = int(matches_df["ga"].sum())

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Matches",   total)
    k2.metric("Wins",      int(wins))
    k3.metric("Draws",     int(draws))
    k4.metric("Losses",    int(losses))
    k5.metric("Goals For", gf)
    k6.metric("Goal Diff", f"{gf - ga:+d}")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='section-label'>Result Breakdown</div>", unsafe_allow_html=True)
        pie_df = pd.DataFrame({
            "Result": ["Win", "Draw", "Loss"],
            "Count":  [int(wins), int(draws), int(losses)]
        })
        fig = px.pie(pie_df, names="Result", values="Count", hole=0.58,
                     color="Result",
                     color_discrete_map={"Win": ACCENT, "Draw": NEUTRAL, "Loss": ACCENT_B})
        fig.update_layout(**PLOT_THEME, showlegend=True,
                          legend=dict(bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.markdown("<div class='section-label'>Goals For vs Against by Season</div>", unsafe_allow_html=True)
        season_goals = matches_df.groupby("season").agg(
            goals_for=("gf", "sum"), goals_against=("ga", "sum")
        ).reset_index()
        fig = go.Figure()
        fig.add_bar(x=season_goals["season"], y=season_goals["goals_for"],
                    name="Goals For", marker_color=ACCENT, marker_line_width=0)
        fig.add_bar(x=season_goals["season"], y=season_goals["goals_against"],
                    name="Goals Against", marker_color=ACCENT_B, marker_line_width=0)
        fig.update_layout(**PLOT_THEME, barmode="group", xaxis_title="", yaxis_title="Goals",
                          legend=dict(bgcolor="rgba(0,0,0,0)"),
                          xaxis=dict(tickfont_color="#888"),
                          yaxis=dict(tickfont_color="#888", gridcolor=GRID))
        st.plotly_chart(fig, width='stretch')

    st.markdown("<div class='section-label'>Home vs Away Performance</div>", unsafe_allow_html=True)
    venue_df = matches_df.groupby("venue").apply(
        lambda x: pd.Series({
            "Matches":       len(x),
            "Wins":          int((x["result"] == "W").sum()),
            "Draws":         int((x["result"] == "D").sum()),
            "Losses":        int((x["result"] == "L").sum()),
            "Goals For":     int(x["gf"].sum()),
            "Goals Against": int(x["ga"].sum()),
        })
    ).reset_index()
    venue_df["Win %"] = (venue_df["Wins"] / venue_df["Matches"] * 100).round(1)
    st.dataframe(venue_df, width='stretch', hide_index=True)

    st.markdown("<div class='section-label'>Match Log</div>", unsafe_allow_html=True)
    display_df = matches_df[["date","season","venue","opponent","gf","ga","result","shots_on_target","yellows"]].copy()
    display_df.columns = ["Date","Season","Venue","Opponent","GF","GA","Result","Shots OT","Yellows"]
    st.dataframe(display_df, width='stretch', hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Head to Head
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Head to Head":
    st.markdown("<div class='page-title'>Head to Head</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Compare two teams across all their meetings</div>", unsafe_allow_html=True)

    teams = get_teams()
    col_a, col_b, col_c = st.columns([2, 2, 1])
    with col_a:
        team_a = st.selectbox("TEAM A", teams,
                               index=teams.index("Barcelona") if "Barcelona" in teams else 0)
    with col_b:
        remaining = [t for t in teams if t != team_a]
        team_b = st.selectbox("TEAM B", remaining, index=0)
    with col_c:
        season_options = ["All Seasons"] + get_seasons()
        h2h_season = st.selectbox("SEASON", season_options)

    season_filter = "" if h2h_season == "All Seasons" else f"AND s.season_label = '{h2h_season}'"

    h2h_df = query(f"""
        SELECT
            s.season_label  AS season,
            d.full_date     AS date,
            ht.team_name    AS home_team,
            at2.team_name   AS away_team,
            f.home_goals, f.away_goals, f.result,
            f.home_shots_on_target, f.away_shots_on_target,
            f.home_corners,         f.away_corners,
            f.home_yellow_cards,    f.away_yellow_cards
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

    def team_result(row, team):
        if row["home_team"] == team:
            return "W" if row["result"] == "H" else ("D" if row["result"] == "D" else "L")
        return "W" if row["result"] == "A" else ("D" if row["result"] == "D" else "L")

    h2h_df["result_a"] = h2h_df.apply(team_result, axis=1, team=team_a)
    wins_a = int((h2h_df["result_a"] == "W").sum())
    draws  = int((h2h_df["result_a"] == "D").sum())
    wins_b = int((h2h_df["result_a"] == "L").sum())
    total  = len(h2h_df)

    goals_a = int(h2h_df.apply(
        lambda r: r["home_goals"] if r["home_team"] == team_a else r["away_goals"], axis=1).sum())
    goals_b = int(h2h_df.apply(
        lambda r: r["home_goals"] if r["home_team"] == team_b else r["away_goals"], axis=1).sum())

    st.markdown(f"""
    <div class='h2h-banner'>
        <div style='text-align:center'>
            <div style='font-size:1.4rem;font-weight:700;color:#111;letter-spacing:-0.02em'>{team_a}</div>
            <div style='font-size:3.2rem;font-weight:800;color:{ACCENT};letter-spacing:-0.04em'>{wins_a}</div>
            <div style='font-family:"DM Mono",monospace;color:#aaa;font-size:0.65rem;letter-spacing:0.1em'>WINS</div>
        </div>
        <div style='text-align:center'>
            <div style='font-family:"DM Mono",monospace;color:#aaa;font-size:0.65rem;letter-spacing:0.1em;margin-bottom:4px'>{total} MEETINGS</div>
            <div style='font-size:2rem;font-weight:700;color:{NEUTRAL}'>{draws}</div>
            <div style='font-family:"DM Mono",monospace;color:#aaa;font-size:0.65rem;letter-spacing:0.1em'>DRAWS</div>
        </div>
        <div style='text-align:center'>
            <div style='font-size:1.4rem;font-weight:700;color:#111;letter-spacing:-0.02em'>{team_b}</div>
            <div style='font-size:3.2rem;font-weight:800;color:{ACCENT_B};letter-spacing:-0.04em'>{wins_b}</div>
            <div style='font-family:"DM Mono",monospace;color:#aaa;font-size:0.65rem;letter-spacing:0.1em'>WINS</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='section-label'>Goals Scored</div>", unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_bar(x=[team_a], y=[goals_a], marker_color=ACCENT,
                    text=[goals_a], textposition="outside", marker_line_width=0)
        fig.add_bar(x=[team_b], y=[goals_b], marker_color=ACCENT_B,
                    text=[goals_b], textposition="outside", marker_line_width=0)
        fig.update_layout(**PLOT_THEME, showlegend=False, yaxis_title="Total Goals",
                          xaxis=dict(tickfont_color="#444", tickfont_size=13),
                          yaxis=dict(tickfont_color="#888", gridcolor=GRID))
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.markdown("<div class='section-label'>Win Share</div>", unsafe_allow_html=True)
        pie_df = pd.DataFrame({
            "Team":  [team_a, "Draw", team_b],
            "Count": [wins_a, draws, wins_b]
        })
        fig = px.pie(pie_df, names="Team", values="Count", hole=0.58,
                     color="Team",
                     color_discrete_map={team_a: ACCENT, "Draw": NEUTRAL, team_b: ACCENT_B})
        fig.update_layout(**PLOT_THEME, legend=dict(bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig, width='stretch')

    st.markdown("<div class='section-label'>Average Match Stats</div>", unsafe_allow_html=True)

    def avg_stat(df, team, home_col, away_col):
        return df.apply(
            lambda r: r[home_col] if r["home_team"] == team else r[away_col], axis=1
        ).mean()

    categories = ["Goals/Match", "Shots on Target", "Corners", "Yellow Cards"]
    vals_a = [
        round(goals_a / total, 2),
        round(avg_stat(h2h_df, team_a, "home_shots_on_target", "away_shots_on_target"), 2),
        round(avg_stat(h2h_df, team_a, "home_corners",         "away_corners"),         2),
        round(avg_stat(h2h_df, team_a, "home_yellow_cards",    "away_yellow_cards"),    2),
    ]
    vals_b = [
        round(goals_b / total, 2),
        round(avg_stat(h2h_df, team_b, "home_shots_on_target", "away_shots_on_target"), 2),
        round(avg_stat(h2h_df, team_b, "home_corners",         "away_corners"),         2),
        round(avg_stat(h2h_df, team_b, "home_yellow_cards",    "away_yellow_cards"),    2),
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals_a, theta=categories, fill="toself", name=team_a,
        line_color=ACCENT, fillcolor="rgba(37,99,235,0.10)"
    ))
    fig.add_trace(go.Scatterpolar(
        r=vals_b, theta=categories, fill="toself", name=team_b,
        line_color=ACCENT_B, fillcolor="rgba(239,68,68,0.10)"
    ))
    fig.update_layout(
        **PLOT_THEME,
        polar=dict(
            bgcolor="#fafaf8",
            radialaxis=dict(visible=True, color="#ccc", gridcolor="#e8e8e4"),
            angularaxis=dict(color="#888")
        ),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        height=400
    )
    st.plotly_chart(fig, width='stretch')

    st.markdown("<div class='section-label'>Match History</div>", unsafe_allow_html=True)
    display = h2h_df[["date","season","home_team","home_goals","away_goals","away_team"]].copy()
    display.columns = ["Date","Season","Home","HG","AG","Away"]
    st.dataframe(display, width='stretch', hide_index=True)