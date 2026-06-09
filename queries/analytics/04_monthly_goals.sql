SELECT
    d.year,
    d.month,
    COUNT(f.match_id)                           AS matches_played,
    SUM(f.home_goals + f.away_goals)            AS total_goals,
    ROUND(AVG(f.home_goals + f.away_goals), 2)  AS avg_goals_per_match
FROM gold.fact_matches f
JOIN gold.dim_date d ON f.date_id = d.date_id
GROUP BY d.year, d.month
ORDER BY d.year, d.month