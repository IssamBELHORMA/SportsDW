SELECT
    CAST(STRFTIME(match_date, '%Y%m%d') AS INTEGER)     AS date_id,
    match_date                                           AS full_date,
    EXTRACT(YEAR  FROM match_date)::INTEGER              AS year,
    EXTRACT(MONTH FROM match_date)::INTEGER              AS month,
    EXTRACT(DAY   FROM match_date)::INTEGER              AS day,
    EXTRACT(WEEK  FROM match_date)::INTEGER              AS week_number,
    STRFTIME(match_date, '%A')                           AS day_of_week,
    CASE
        WHEN STRFTIME(match_date, '%A') IN ('Saturday','Sunday')
        THEN true ELSE false
    END                                                  AS is_weekend
FROM (
    SELECT DISTINCT match_date
    FROM {{ ref('silver_matches') }}
    WHERE match_date IS NOT NULL
)
ORDER BY match_date