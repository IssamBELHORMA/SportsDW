SELECT
    t.team_name,
    COUNT(f.match_id)                                        AS total_matches,
    SUM(CASE WHEN f.team_id_home = t.team_id
             AND f.result = 'H' THEN 1
             WHEN f.team_id_away = t.team_id
             AND f.result = 'A' THEN 1
             ELSE 0 END)                                     AS wins,
    SUM(CASE WHEN f.result = 'D' THEN 1 ELSE 0 END)         AS draws,
    SUM(CASE WHEN f.team_id_home = t.team_id
             AND f.result = 'A' THEN 1
             WHEN f.team_id_away = t.team_id
             AND f.result = 'H' THEN 1
             ELSE 0 END)                                     AS losses,
    SUM(CASE WHEN f.team_id_home = t.team_id
             THEN f.home_goals ELSE f.away_goals END)        AS goals_scored,
    SUM(CASE WHEN f.team_id_home = t.team_id
             THEN f.away_goals ELSE f.home_goals END)        AS goals_conceded,
    SUM(CASE WHEN f.team_id_home = t.team_id
             THEN f.home_goals ELSE f.away_goals END) -
    SUM(CASE WHEN f.team_id_home = t.team_id
             THEN f.away_goals ELSE f.home_goals END)        AS goal_difference
FROM gold.fact_matches f
JOIN gold.dim_team t
    ON t.team_id IN (f.team_id_home, f.team_id_away)
GROUP BY t.team_id, t.team_name
ORDER BY wins DESC, goal_difference DESC