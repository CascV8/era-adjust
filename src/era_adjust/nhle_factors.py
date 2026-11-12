"""Season-by-season NHLe: what a junior, college or European season is worth in NHL points.

The factors come from the NHLe network (CascV8/NHLe, training/seasons.py): each league's
network factor, allowed to move from season to season by that season's crossovers, with a
step at the 2025-26 rule change (CHL players keep NCAA eligibility) for the NCAA, OHL, WHL
and QMJHL. ``data/nhle_factors.csv`` holds the table.

A factor turns league points into NHL points *of the same season*. To restate them in another
NHL season's scoring, they're multiplied by that season's NHL point factor (``adjust``).
"""

from functools import lru_cache
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

from .adjust import table as nhl_table
from .data import ROOT, season_label

NHLE_CSV = ROOT / "data" / "nhle_factors.csv"
SOURCE_URL = "https://raw.githubusercontent.com/CascV8/NHLe/nhle-models/training/factors_by_season.csv"
RULE_CHANGE = 2025


@lru_cache(maxsize=1)
def factors() -> pd.DataFrame:
    """The NHLe table: one row per league and season (league, season, factor, log_se, network_factor, players)."""
    if not NHLE_CSV.exists():
        raise FileNotFoundError(f"{NHLE_CSV} is missing: run `uv run era-adjust build-nhle` first")
    return pd.read_csv(NHLE_CSV)


def leagues() -> list[str]:
    return sorted(factors().league.unique())


def factor(league: str, season: int) -> float:
    """NHL points per league point in ``season``. A season after the table's last uses the last
    one (the rule-change step included); a season before its first uses the first."""
    league = league.lower()
    df = factors()
    rows = df[df.league == league]
    if rows.empty:
        raise ValueError(f"no NHLe factor for {league!r}; leagues: {', '.join(leagues())}")
    season = min(max(season, int(rows.season.min())), int(rows.season.max()))
    return float(rows.loc[rows.season == season, "factor"].iloc[0])


def nhle(league: str, season: int, points: float, gp: float | None = None,
         to: int | None = None, per: float = 82) -> dict:
    """A league season's points as NHL points: in ``season``'s NHL scoring, and with ``to``
    restated in that NHL season's scoring (points per team-game). With ``gp``, also per ``per`` games."""
    f = factor(league, season)
    pts = points * f
    out = {"league": league.lower(), "season": season_label(season), "points": points, "gp": gp,
           "factor": f, "nhle": pts, "to": None, "era_factor": 1.0}
    if to is not None:
        nhl = nhl_table()
        src = min(season, int(nhl.index.max()))   # a league season past the NHL table: its latest season
        if src not in nhl.index:
            raise ValueError(f"no NHL season {season_label(src)} to compare with")
        if to not in nhl.index:
            raise ValueError(f"no NHL season {season_label(to)}")
        out["era_factor"] = float(nhl.loc[to, "ppg"] / nhl.loc[src, "ppg"])
        out["to"] = season_label(to)
    out["adj_nhle"] = pts * out["era_factor"]
    out[f"per{per:g}"] = out["adj_nhle"] / gp * per if gp else None
    return out


def build(source: str | Path | None = None) -> pd.DataFrame:
    """Copy the NHLe table from a local factors_by_season.csv, or download it from the NHLe repo."""
    source = source or SOURCE_URL
    if str(source).startswith("http"):
        with urlopen(str(source), timeout=60) as r:
            text = r.read().decode("utf-8")
    else:
        text = Path(source).read_text(encoding="utf-8")
    NHLE_CSV.parent.mkdir(parents=True, exist_ok=True)
    NHLE_CSV.write_text(text, encoding="utf-8")
    factors.cache_clear()
    return factors()
