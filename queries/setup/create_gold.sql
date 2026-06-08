CREATE SCHEMA IF NOT EXISTS gold;




CREATE OR REPLACE TABLE gold.dim_season AS
SELECT
    ROW_NUMBER() OVER (ORDER BY season) AS season_id,
    season                              AS season_label,
    CAST('20' || LEFT(season, 2) AS INTEGER) AS start_year,
    CAST('20' || RIGHT(season, 2) AS INTEGER) AS end_year
FROM (
    SELECT DISTINCT season
    FROM bronze.matches_raw
)
ORDER BY season;




CREATE OR REPLACE TABLE gold.dim_team AS
SELECT
    ROW_NUMBER() OVER (ORDER BY team_name) AS team_id,
    team_name
FROM (
    SELECT DISTINCT HomeTeam AS team_name FROM bronze.matches_raw
    UNION
    SELECT DISTINCT AwayTeam AS team_name FROM bronze.matches_raw
)
ORDER BY team_name;




CREATE OR REPLACE TABLE gold.dim_date AS
SELECT
    CAST(STRFTIME(full_date, '%Y%m%d') AS INTEGER) AS date_id,
    full_date,
    EXTRACT(YEAR    FROM full_date)::INTEGER AS year,
    EXTRACT(MONTH   FROM full_date)::INTEGER AS month,
    EXTRACT(DAY     FROM full_date)::INTEGER AS day,
    EXTRACT(WEEK    FROM full_date)::INTEGER AS week_number,
    STRFTIME(full_date, '%A')                AS day_of_week,
    CASE
        WHEN STRFTIME(full_date, '%A') IN ('Saturday', 'Sunday')
        THEN true ELSE false
    END AS is_weekend
FROM (
    SELECT DISTINCT CAST(Date AS DATE) AS full_date
    FROM bronze.matches_raw
    WHERE Date IS NOT NULL
)
ORDER BY full_date;




CREATE OR REPLACE TABLE gold.fact_matches AS
SELECT
    ROW_NUMBER() OVER (ORDER BY m.Date, m.HomeTeam) AS match_id,

    -- foreign keys
    ds.season_id,
    home.team_id                                     AS team_id_home,
    away.team_id                                     AS team_id_away,
    CAST(STRFTIME(CAST(m.Date AS DATE), '%Y%m%d')
         AS INTEGER)                                 AS date_id,

    -- match result
    m.FTHG                                           AS home_goals,
    m.FTAG                                           AS away_goals,
    m.FTR                                            AS result,
    m.HTHG                                           AS home_goals_ht,
    m.HTAG                                           AS away_goals_ht,
    m.HTR                                            AS result_ht,

    -- match stats
    m.HS                                             AS home_shots,
    m.AS                                             AS away_shots,
    m.HST                                            AS home_shots_on_target,
    m.AST                                            AS away_shots_on_target,
    m.HF                                             AS home_fouls,
    m.AF                                             AS away_fouls,
    m.HC                                             AS home_corners,
    m.AC                                             AS away_corners,
    m.HY                                             AS home_yellow_cards,
    m.AY                                             AS away_yellow_cards,
    m.HR                                             AS home_red_cards,
    m.AR                                             AS away_red_cards

FROM bronze.matches_raw m

-- join to get season_id
JOIN gold.dim_season ds
    ON m.season = ds.season_label

-- join twice to dim_team for home and away
JOIN gold.dim_team home
    ON m.HomeTeam = home.team_name

JOIN gold.dim_team away
    ON m.AwayTeam = away.team_name

ORDER BY m.Date, m.HomeTeam;