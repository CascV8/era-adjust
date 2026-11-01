"""Season-over-season era factors.

For every season the scoring environment is measured as goals per team-game (GPG) and
assists per team-game (APG = GPG x league assists per goal). Each season is compared to
the season played before it (2005-06 is compared to 2003-04, as 2004-05 was not played):

    goal_factor_vs_prev = GPG(prev) / GPG(season)

Multiplying a season's goals by that factor restates them in the previous season's
scoring environment. Chaining the factors season by season links any season to a
reference season:

    goal_factor_to_ref = product of the season-over-season factors between the two
                       = GPG(ref) / GPG(season)

The same holds for assists, and for schedule length (games per team) when per-82-game
style scaling is wanted.
"""

import numpy as np
import pandas as pd

from .data import season_label


def compute(totals: pd.DataFrame, ref: int | None = None, current: int | None = None) -> pd.DataFrame:
    """Factor table from the per-season totals in ``data.all_totals``.

    ``ref`` defaults to the latest complete season. ``current`` marks the season under way
    as partial (its numbers move until the season ends).
    """
    df = totals.sort_values("season").reset_index(drop=True).copy()
    df["label"] = df["season"].map(season_label)
    df["partial"] = df["season"] == current if current is not None else False
    df["games_per_team"] = df["max_gp"]  # schedule length: most games any team played

    df["gpg"] = df["goals"] / df["team_games"]
    df["assists_per_goal"] = df["assists"] / df["skater_goals"].replace(0, np.nan)
    df["apg"] = df["gpg"] * df["assists_per_goal"]
    df["ppg"] = df["gpg"] + df["apg"]

    df["prev_season"] = df["season"].shift(1).astype("Int64")
    for stat in ("gpg", "apg", "ppg"):
        prev = df[stat].shift(1)
        df[f"{stat}_change_pct"] = (df[stat] / prev - 1) * 100
    df["goal_factor_vs_prev"] = df["gpg"].shift(1) / df["gpg"]
    df["assist_factor_vs_prev"] = df["apg"].shift(1) / df["apg"]
    df["point_factor_vs_prev"] = df["ppg"].shift(1) / df["ppg"]

    if ref is None:
        complete = df.loc[~df["partial"], "season"]
        ref = int(complete.max())
    if ref not in set(df["season"]):
        raise ValueError(f"no NHL season {season_label(ref)} in the table")
    df.attrs["ref"] = ref

    i_ref = int(df.index[df["season"] == ref][0])
    for kind in ("goal", "assist", "point"):
        yoy = df[f"{kind}_factor_vs_prev"].fillna(1.0).to_numpy()
        # chain[i] = GPG(first) / GPG(i), so chain[i] / chain[ref] = GPG(ref) / GPG(i).
        chain = np.cumprod(yoy)
        df[f"{kind}_factor_to_ref"] = chain / chain[i_ref]
    return df


COLUMNS = [
    "label", "partial", "teams", "games_per_team", "gpg", "gpg_change_pct", "goal_factor_vs_prev",
    "assists_per_goal", "apg", "apg_change_pct", "assist_factor_vs_prev",
    "goal_factor_to_ref", "assist_factor_to_ref",
]
