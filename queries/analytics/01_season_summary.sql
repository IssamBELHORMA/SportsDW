SELECT
    s.season_label,
    COUNT(f.match_id)                                    AS total_matches,
    SUM(f.home_goals + f.away_goals)                     AS total_goals,
    ROUND(AVG(f.home_goals + f.away_goals), 2)           AS avg_goals_per_match,
    SUM(CASE WHEN f.result = 'H' THEN 1 ELSE 0 END)     AS home_wins,
    SUM(CASE WHEN f.result = 'D' THEN 1 ELSE 0 END)     AS draws,
    SUM(CASE WHEN f.result = 'A' THEN 1 ELSE 0 END)     AS away_wins,
    ROUND(100.0 * SUM(CASE WHEN f.result = 'H' THEN 1 ELSE 0 END)
          / COUNT(*), 1)                                 AS home_win_pct
FROM gold.fact_matches f
JOIN gold.dim_season s ON f.season_id = s.season_id
GROUP BY s.season_label
ORDER BY s.season_label