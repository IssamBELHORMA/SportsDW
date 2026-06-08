# Football-Data.co.uk Data Dictionary & Schema Documentation

This documentation provides an exhaustive reference for the CSV data structures provided by [football-data.co.uk](https://www.football-data.co.uk), specifically tailored for European leagues like LaLiga (Primera & Segunda División).

---

## 1. Core Match Metadata

These columns provide fundamental historical context for each fixture, including dates, structural divisions, and competing clubs.

| Column | Full Name | Description | Data Type / Format | Example |
| :--- | :--- | :--- | :--- | :--- |
| **Div** | Division | The specific league tier. | String | `SP1` (LaLiga), `SP2` (Segunda) |
| **Date** | Match Date | The scheduled date of the fixture. | Date (`dd/mm/yy` or `dd/mm/yyyy`) | `12/08/23` |
| **Time** | Kick-off Time | Official match start time (UK time). | Time (`hh:mm`) | `20:30` |
| **HomeTeam** | Home Team | The club playing in their home stadium. | String | `Real Madrid` |
| **AwayTeam** | Away Team | The visiting club. | String | `Barcelona` |

---

## 2. Match Results & Scorelines

Tracks full-time and halftime performance metrics used to evaluate outright outcomes.

| Column | Full Name | Description | Format / Values |
| :--- | :--- | :--- | :--- |
| **FTHG** | Full-Time Home Goals | Number of goals scored by the home team. | Integer |
| **FTAG** | Full-Time Away Goals | Number of goals scored by the away team. | Integer |
| **FTR** | Full-Time Result | Final match result. | `H` (Home Win), `D` (Draw), `A` (Away Win) |
| **HTHG** | Half-Time Home Goals | Home team goals scored in the first half. | Integer |
| **HTAG** | Half-Time Away Goals | Away team goals scored in the first half. | Integer |
| **HTR** | Half-Time Result | Match state at the halftime whistle. | `H` (Home Win), `D` (Draw), `A` (Away Win) |

---

## 3. In-Game Match Performance Statistics

Crucial for advanced analytical models (e.g., Expected Goals, defensive resilience, discipline tracking).

| Column | Full Name | Description | Target Team |
| :--- | :--- | :--- | :--- |
| **Referee** | Match Referee | The primary official managing the fixture. | N/A |
| **HS** | Home Shots | Total shot attempts (including off-target & blocked). | Home |
| **AS** | Away Shots | Total shot attempts (including off-target & blocked). | Away |
| **HST** | Home Shots on Target | Shots testing the keeper, hitting the post, or scoring. | Home |
| **AST** | Away Shots on Target | Shots testing the keeper, hitting the post, or scoring. | Away |
| **HF** | Home Fouls | Total fouls penalized by the referee. | Home |
| **AF** | Away Fouls | Total fouls penalized by the referee. | Away |
| **HC** | Home Corners | Total corner kicks awarded. | Home |
| **AC** | Away Corners | Total corner kicks awarded. | Away |
| **HY** | Home Yellow Cards | Cautions issued to home players. | Home |
| **AY** | Away Yellow Cards | Cautions issued to away players. | Away |
| **HR** | Home Red Cards | Direct or indirect ejections issued to home players. | Home |
| **AR** | Away Red Cards | Direct or indirect ejections issued to home players. | Away |

---

## 4. Betting Odds Architecture

The dataset includes extensive coverage of bookmaker odds. These columns are named dynamically using combinations of **Bookmaker Identifiers** (prefixes) and **Market Outcomes** (suffixes).

### 4.1 Major Bookmaker Codes (Prefixes)
* **B365**: Bet365
* **BW**: Bwin
* **IW**: Interwetten
* **WH**: William Hill
* **PS / P**: Pinnacle Sports
* **VC**: BetVictor
* **Max**: Market Maximum (highest available odds tracked across portals)
* **Avg**: Market Average (mean value of tracked bookmaker odds)

### 4.2 Standard 1X2 Traditional Outright Markets
These columns combine a bookmaker prefix with a final result outcome suffix (`H`, `D`, `A`).

* **`[Bookmaker]H`**: Odds for a Home Win (e.g., `B365H`, `PWH`, `MaxH`).
* **`[Bookmaker]D`**: Odds for a Draw (e.g., `B365D`, `IWD`, `AvgD`).
* **`[Bookmaker]A`**: Odds for an Away Win (e.g., `B365A`, `PSA`, `MaxA`).

### 4.3 Over / Under 2.5 Total Goals Market
Tracks pricing for total combined match scoring thresholds.

* **`[Bookmaker]>2.5`**: Odds for 3 or more total goals scored (e.g., `B365>2.5`, `P>2.5`).
* **`[Bookmaker]<2.5`**: Odds for 2 or fewer total goals scored (e.g., `B365<2.5`, `P<2.5`).

### 4.4 Asian Handicap Markets
Provides options eliminating the draw outcome by offering spread parameters.

* **`BbMx>2.5` / `BbAv>2.5`**: Betbrain historical maximum/average over 2.5 goals (found in older historical seasons).
* **`AHh`**: Asian Handicap line size/spread (e.g., `-0.5`, `+1.25`).
* **`[Bookmaker]AHH`**: Odds for Home Team with selected Asian Handicap line.
* **`[Bookmaker]AHA`**: Odds for Away Team with selected Asian Handicap line.

---

## 5. Market Dynamics: Opening vs. Closing Odds

Modern seasons track the evolution of financial market movements by recording odds at two critical time points:

1. **Opening Odds (Standard Prefix):** The odds offered when the market originally stabilized (e.g., `B365H`, `Max>2.5`).
2. **Closing Odds (`C` Prefix):** The definitive line right before the match kicks off, incorporating all public information and late team news.
   * **`CB365H`**: Closing Home Win odds at Bet365.
   * **`CMax>2.5`**: Closing Maximum market odds for the Over 2.5 goals line.
   * **`CAvgA`**: Closing Average market odds for an Away Win.

---

### Analytical Best Practices

* **Advanced Metric Generation:** Combine `HST`/`HS` and `AST`/`AS` to calculate team-level shot accuracy percentages.
* **Closing Line Value (CLV):** Compare standard opening columns against closing `C` columns to analyze market shifts, public sentiment betting trends, and line sharp pricing movements.