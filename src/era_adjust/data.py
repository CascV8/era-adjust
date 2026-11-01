"""League scoring totals for every NHL regular season, from stats.nhl.com via puckscrape."""

from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
FACTORS_CSV = ROOT / "data" / "era_factors.csv"
FIRST_SEASON = 1917  # 1917-18


def season_label(season: int) -> str:
    return f"{season}-{(season + 1) % 100:02d}"


def current_season(today: date | None = None) -> int:
    """The season under way (or just finished) on ``today``; it starts in October."""
    today = today or date.today()
    return today.year if today.month >= 9 else today.year - 1


def season_totals(season: int, refresh: bool = False) -> dict | None:
    """Goals, assists and team-games for one season, or None when no games were played (2004-05).

    Finished seasons are cached in data/raw; the season under way is always fetched.
    """
    import puckscrape.nhl as nhl

    cache = RAW / f"{season}.csv"
    live = season >= current_season()
    if cache.exists() and not refresh and not live:
        row = pd.read_csv(cache).iloc[0].to_dict()
        return None if row["teams"] == 0 else row

    teams = nhl.team_stats(season)
    skaters = nhl.skater_stats(season) if len(teams) else pd.DataFrame()
    row = {
        "season": season,
        "teams": len(teams),
        "team_games": int(teams["games_played"].sum()) if len(teams) else 0,
        "goals": int(teams["goals_for"].sum()) if len(teams) else 0,
        "skater_goals": int(skaters["goals"].sum()) if len(skaters) else 0,
        "assists": int(skaters["assists"].sum()) if len(skaters) else 0,
        "max_gp": int(teams["games_played"].max()) if len(teams) else 0,
    }
    if not live:
        RAW.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([row]).to_csv(cache, index=False)
    return None if row["teams"] == 0 else row


def all_totals(refresh: bool = False, through: int | None = None) -> pd.DataFrame:
    """One row per season that was played, 1917-18 through the season under way."""
    through = through if through is not None else current_season()
    rows = []
    for season in range(FIRST_SEASON, through + 1):
        row = season_totals(season, refresh=refresh)
        if row is not None and row["team_games"] > 0:
            rows.append(row)
    return pd.DataFrame(rows)
