WITH team_season_stats AS (
    SELECT
        t.team_name,
        s.season_label,
        SUM(CASE WHEN f.team_id_home = t.team_id
                 THEN f.home_goals ELSE f.away_goals END)    AS goals_scored,
        COUNT(f.match_id)                                    AS matches,
        RANK() OVER (
            PARTITION BY s.season_label
            ORDER BY SUM(CASE WHEN f.team_id_home = t.team_id
                              THEN f.home_goals
                              ELSE f.away_goals END) DESC
        )                                                    AS rank_in_season
    FROM gold.fact_matches f
    JOIN gold.dim_team   t ON t.team_id IN (f.team_id_home, f.team_id_away)
    JOIN gold.dim_season s ON f.season_id = s.season_id
    GROUP BY t.team_name, s.season_label, t.team_id
)
SELECT
    season_label,
    team_name,
    goals_scored,
    matches,
    rank_in_season
FROM team_season_stats
WHERE rank_in_season <= 3
ORDER BY season_label, rank_in_season