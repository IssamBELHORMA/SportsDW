SELECT
    -- identity
    season,
    CAST(Date AS DATE)                              AS match_date,
    Time                                            AS match_time,
    HomeTeam                                        AS home_team,
    AwayTeam                                        AS away_team,

    -- full time
    FTHG                                            AS home_goals,
    FTAG                                            AS away_goals,
    FTR                                             AS result,

    -- half time
    HTHG                                            AS home_goals_ht,
    HTAG                                            AS away_goals_ht,
    HTR                                             AS result_ht,

    -- stats
    HS                                              AS home_shots,
    "AS"                                            AS away_shots,
    HST                                             AS home_shots_on_target,
    AST                                             AS away_shots_on_target,
    HF                                              AS home_fouls,
    AF                                              AS away_fouls,
    HC                                              AS home_corners,
    AC                                              AS away_corners,
    HY                                              AS home_yellow_cards,
    AY                                              AS away_yellow_cards,
    HR                                              AS home_red_cards,
    AR                                              AS away_red_cards

FROM {{ ref('bronze_matches') }}