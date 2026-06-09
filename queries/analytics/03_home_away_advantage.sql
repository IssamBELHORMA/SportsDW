SELECT
    t.team_name,
    COUNT(CASE WHEN f.team_id_home = t.team_id THEN 1 END)   AS home_matches,
    COUNT(CASE WHEN f.team_id_away = t.team_id THEN 1 END)   AS away_matches,
    ROUND(100.0 * SUM(CASE WHEN f.team_id_home = t.team_id
                           AND f.result = 'H' THEN 1 ELSE 0 END)
          / NULLIF(COUNT(CASE WHEN f.team_id_home = t.team_id
                              THEN 1 END), 0), 1)             AS home_win_pct,
    ROUND(100.0 * SUM(CASE WHEN f.team_id_away = t.team_id
                           AND f.result = 'A' THEN 1 ELSE 0 END)
          / NULLIF(COUNT(CASE WHEN f.team_id_away = t.team_id
                              THEN 1 END), 0), 1)             AS away_win_pct
FROM gold.fact_matches f
JOIN gold.dim_team t
    ON t.team_id IN (f.team_id_home, f.team_id_away)
GROUP BY t.team_id, t.team_name
HAVING COUNT(f.match_id) >= 30
ORDER BY home_win_pct DESC