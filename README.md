# era-adjust

NHL era adjustment: every regular season since 1917-18 compared to the season before it, built on
[puckscrape](https://github.com/CascV8/Puckscrape) (stats.nhl.com team and skater totals).

The scoring environment of a season is its goals per team-game (GPG) and assists per team-game
(APG = GPG × league assists per goal). Each season gets a factor against the previous one:

```
goal_factor_vs_prev = GPG(previous season) / GPG(season)
```

Multiply a season's goals by it to restate them in the previous season's scoring. 2005-06 is compared
to 2003-04, since 2004-05 wasn't played. The season-over-season factors chain together, which links
any season to a reference season (default: the latest complete one, 2025-26):
`goal_factor_to_ref = GPG(ref) / GPG(season)`. Assists and points work the same way.

`data/era_factors.csv` holds the table, so it works without downloading.

## Use

```
uv sync
uv run era-adjust table                               # every season vs the one before
uv run era-adjust table --from 2000 --ref 1985        # a range, chained to 1985-86
uv run era-adjust adjust 2025 -g 50 -a 50             # 2025-26 line in 2024-25 terms
uv run era-adjust adjust 1981-82 -g 92 -a 120 --gp 80 --to 2025 --schedule
#   -> 72.4 G, 96.8 A, 169.3 P in 82 GP (2025-26 terms)
uv run era-adjust build                               # re-download (finished seasons are cached in data/raw)
```

```python
from era_adjust import adjust, table

adjust(1981, goals=92, assists=120, to=2025)["adj_goals"]   # 70.7
table().loc[2005, ["gpg", "gpg_change_pct", "goal_factor_vs_prev"]]
```

Seasons can be written `2024`, `2024-25` or `20242025`. A bare year is the season that starts then.

## Columns

| column | meaning |
|---|---|
| `gpg`, `apg`, `ppg` | goals / assists / points per team-game |
| `*_change_pct` | % change from the previous season |
| `goal_factor_vs_prev`, `assist_factor_vs_prev`, `point_factor_vs_prev` | multiply to restate in the previous season's terms |
| `*_factor_to_ref` | chained factors to the reference season |
| `games_per_team` | schedule length (most games any team played) |
| `partial` | the season under way; its numbers move until it ends |

## NHLe by season

`data/nhle_factors.csv` holds NHLe factors (NHL points per league point) for 46 leagues, season by
season from 2010-11, from the [NHLe](https://github.com/CascV8/NHLe) network (`training/seasons.py`).
Each league's network factor can move from season to season by that season's crossover players
(shrunk toward the league's level: the fit puts the typical season-to-season move at about 5%).
For the NCAA, OHL, WHL and QMJHL it can also step from 2025-26 on, when CHL players got to keep NCAA eligibility.
That step has a ±15% prior and only moves as far as the post-change seasons show. With one season so far
(and the 2026 World Juniors still thin in the data) it is about ×1.00 for the NCAA, ×1.07 OHL,
×0.98 WHL and ×1.15 QMJHL, each about ±11–14%: not distinguishable from no change yet.

```
uv run era-adjust nhle ohl 2023-24 -p 102 --gp 68 --to 2025   # OHL points as NHL points, in 2025-26 scoring
uv run era-adjust nhle-table ncaa ohl whl qmjhl --from 2020
uv run era-adjust build-nhle                                   # re-download from the NHLe repo (--source for a local csv)
```

```python
from era_adjust import nhle
nhle("ohl", 2023, points=102, gp=68, to=2025)["per82"]
```

The factor gives NHL points in the *same* season's NHL; `--to` multiplies by the NHL's points per
team-game ratio to restate them in another season. Seasons after the table use its last season.

## Caveats

- Assists were awarded sparingly before the 1930s (0.4–0.6 assists per goal in the earliest seasons,
  against about 1.7 today), so assist factors to modern seasons from that era are very small.
- The adjustment is league-wide scoring only. It doesn't account for roster size, ice time or
  power-play rates.
