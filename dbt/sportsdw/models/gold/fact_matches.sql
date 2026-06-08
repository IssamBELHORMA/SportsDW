SELECT
    ROW_NUMBER() OVER (ORDER BY s.match_date, s.home_team)  AS match_id,

    -- foreign keys
    ds.season_id,
    home.team_id                                             AS team_id_home,
    away.team_id                                             AS team_id_away,
    CAST(STRFTIME(s.match_date, '%Y%m%d') AS INTEGER)       AS date_id,

    -- result
    s.home_goals,
    s.away_goals,
    s.result,
    s.home_goals_ht,
    s.away_goals_ht,
    s.result_ht,

    -- stats
    s.home_shots,
    s.away_shots,
    s.home_shots_on_target,
    s.away_shots_on_target,
    s.home_fouls,
    s.away_fouls,
    s.home_corners,
    s.away_corners,
    s.home_yellow_cards,
    s.away_yellow_cards,
    s.home_red_cards,
    s.away_red_cards

FROM {{ ref('silver_matches') }} s
JOIN {{ ref('dim_season') }}     ds   ON s.season       = ds.season_label
JOIN {{ ref('dim_team') }}       home ON s.home_team     = home.team_name
JOIN {{ ref('dim_team') }}       away ON s.away_team     = away.team_name