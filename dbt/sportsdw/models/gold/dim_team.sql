SELECT
    ROW_NUMBER() OVER (ORDER BY team_name)  AS team_id,
    team_name
FROM (
    SELECT DISTINCT home_team AS team_name FROM {{ ref('silver_matches') }}
    UNION
    SELECT DISTINCT away_team AS team_name FROM {{ ref('silver_matches') }}
)
ORDER BY team_name