"""NHL era adjustment: every season compared to the season before it."""

import argparse

import pandas as pd

from . import adjust as _adjust, data, factors
from .adjust import adjust, previous_season, table

__all__ = ["adjust", "previous_season", "table", "main"]


def _season(text: str) -> int:
    """2024, 2024-25, 2024-2025 or 20242025 -> 2024 (the year the season starts)."""
    digits = text.replace("-", "").replace("/", "")
    return int(digits[:4])


def cmd_build(args):
    totals = data.all_totals(refresh=args.refresh)
    cur = data.current_season()
    df = factors.compute(totals, ref=args.ref, current=cur)
    data.FACTORS_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(data.FACTORS_CSV, index=False, float_format="%.6g")
    _adjust.table.cache_clear()
    print(f"{len(df)} seasons ({df['label'].iloc[0]} to {df['label'].iloc[-1]}), "
          f"reference {data.season_label(df.attrs['ref'])} -> {data.FACTORS_CSV}")


def cmd_table(args):
    df = table().reset_index()
    if args.ref is not None:
        totals = df[["season", "teams", "team_games", "goals", "skater_goals", "assists", "max_gp"]]
        df = factors.compute(totals, ref=args.ref, current=data.current_season())
    if args.start is not None:
        df = df[df["season"] >= args.start]
    if args.end is not None:
        df = df[df["season"] <= args.end]
    out = df[factors.COLUMNS].copy()
    out["partial"] = out["partial"].map({True: "*", False: ""})
    with pd.option_context("display.max_rows", None, "display.width", 250, "display.float_format", "{:.3f}".format):
        print(out.to_string(index=False))
    if (df["partial"] == True).any():
        print("* season under way: its numbers move until it ends")


def cmd_adjust(args):
    r = adjust(args.season, args.goals, args.assists, gp=args.gp, to=args.to, schedule=args.schedule)
    gp = f" in {r['gp']:.0f} GP" if r["gp"] is not None else ""
    print(f"{r['season']}: {r['goals']:g} G, {r['assists']:g} A, {r['points']:g} P")
    print(f"in {r['to']} terms{gp}: {r['adj_goals']:.1f} G, {r['adj_assists']:.1f} A, {r['adj_points']:.1f} P")
    print(f"goal factor {r['goal_factor']:.3f}, assist factor {r['assist_factor']:.3f}"
          + (f", schedule factor {r['schedule_factor']:.3f}" if args.schedule else ""))


def main(argv=None):
    p = argparse.ArgumentParser(prog="era-adjust", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="download league totals for every season and write data/era_factors.csv")
    b.add_argument("--refresh", action="store_true", help="re-download finished seasons too")
    b.add_argument("--ref", type=_season, help="reference season for the chained factors (default: latest complete)")
    b.set_defaults(func=cmd_build)

    t = sub.add_parser("table", help="print the factor table")
    t.add_argument("--from", dest="start", type=_season)
    t.add_argument("--to", dest="end", type=_season)
    t.add_argument("--ref", type=_season, help="chain the factors to this season instead")
    t.set_defaults(func=cmd_table)

    a = sub.add_parser("adjust", help="restate a stat line in another season's scoring (default: the season before)")
    a.add_argument("season", type=_season)
    a.add_argument("-g", "--goals", type=float, default=0)
    a.add_argument("-a", "--assists", type=float, default=0)
    a.add_argument("--gp", type=float)
    a.add_argument("--to", type=_season, help="target season (default: the previous season)")
    a.add_argument("--schedule", action="store_true", help="also scale to the target season's games per team")
    a.set_defaults(func=cmd_adjust)

    args = p.parse_args(argv)
    args.func(args)
