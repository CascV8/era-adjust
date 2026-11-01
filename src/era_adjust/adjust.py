"""Era-adjust a stat line with the factor table."""

from functools import lru_cache

import pandas as pd

from .data import FACTORS_CSV, season_label


@lru_cache(maxsize=1)
def table() -> pd.DataFrame:
    """The factor table written by ``era-adjust build`` (data/era_factors.csv), indexed by season."""
    if not FACTORS_CSV.exists():
        raise FileNotFoundError(f"{FACTORS_CSV} is missing: run `uv run era-adjust build` first")
    return pd.read_csv(FACTORS_CSV).set_index("season")


def _row(df: pd.DataFrame, season: int) -> pd.Series:
    if season not in df.index:
        raise ValueError(f"no NHL season {season_label(season)} (2004-05 was not played)")
    return df.loc[season]


def previous_season(season: int) -> int:
    prev = _row(table(), season)["prev_season"]
    if pd.isna(prev):
        raise ValueError(f"{season_label(season)} is the first NHL season")
    return int(prev)


def adjust(season: int, goals: float = 0, assists: float = 0, gp: float | None = None,
           to: int | None = None, schedule: bool = False) -> dict:
    """Restate a season's goals and assists in another season's scoring environment.

    ``to`` defaults to the season before ``season``. With ``schedule=True`` (and ``gp``) the
    line is also scaled to the target season's games per team.
    """
    df = table()
    src = _row(df, season)
    to = previous_season(season) if to is None else to
    dst = _row(df, to)

    g_factor = dst["gpg"] / src["gpg"]
    a_factor = dst["apg"] / src["apg"]
    sched = dst["games_per_team"] / src["games_per_team"] if schedule else 1.0

    adj_g = goals * g_factor * sched
    adj_a = assists * a_factor * sched
    return {
        "season": season_label(season),
        "to": season_label(to),
        "goals": goals, "assists": assists, "points": goals + assists,
        "gp": gp * sched if gp is not None else None,
        "goal_factor": g_factor, "assist_factor": a_factor, "schedule_factor": sched,
        "adj_goals": adj_g, "adj_assists": adj_a, "adj_points": adj_g + adj_a,
    }
