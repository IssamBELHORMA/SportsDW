SELECT
    ROW_NUMBER() OVER (ORDER BY season_label)           AS season_id,
    season_label,
    CAST('20' || LEFT(season_label, 2) AS INTEGER)      AS start_year,
    CAST('20' || RIGHT(season_label, 2) AS INTEGER)     AS end_year
FROM (
    SELECT DISTINCT season AS season_label
    FROM {{ ref('silver_matches') }}
)
ORDER BY season_label