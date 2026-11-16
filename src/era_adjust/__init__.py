"""NHL era adjustment: every season compared to the season before it, and season-by-season NHLe."""

import argparse

import pandas as pd

from . import adjust as _adjust, data, factors, nhle_chart as _chart, nhle_factors as _nhle
from .adjust import adjust, previous_season, table
from .nhle_factors import nhle

__all__ = ["adjust", "nhle", "previous_season", "table", "main"]


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


def cmd_build_nhle(args):
    df = _nhle.build(args.source)
    print(f"{df.league.nunique()} leagues, {data.season_label(int(df.season.min()))} to "
          f"{data.season_label(int(df.season.max()))} -> {_nhle.NHLE_CSV}")


def cmd_nhle_table(args):
    df = _nhle.factors()
    if args.leagues:
        df = df[df.league.isin([lg.lower() for lg in args.leagues])]
        if df.empty:
            raise SystemExit(f"no such league; leagues: {', '.join(_nhle.leagues())}")
    if args.start is not None:
        df = df[df.season >= args.start]
    if args.end is not None:
        df = df[df.season <= args.end]
    wide = df.pivot(index="league", columns="season", values="factor")
    wide.columns = [f"{s % 100:02d}-{(s + 1) % 100:02d}" for s in wide.columns]
    with pd.option_context("display.max_rows", None, "display.width", 250, "display.float_format", "{:.3f}".format):
        print(wide.to_string())
    if (df.season >= _nhle.RULE_CHANGE).any() and df.league.isin(["ncaa", "ohl", "whl", "qmjhl"]).any():
        print(f"NCAA/OHL/WHL/QMJHL from {data.season_label(_nhle.RULE_CHANGE)} include the rule-change step")


def cmd_nhle(args):
    r = _nhle.nhle(args.league, args.season, args.points, gp=args.gp, to=args.to, per=args.per)
    gp = f" in {r['gp']:g} GP" if r["gp"] else ""
    print(f"{r['league'].upper()} {r['season']}: {r['points']:g} P{gp}, NHLe factor {r['factor']:.3f}")
    print(f"NHLe ({r['season']} NHL): {r['nhle']:.1f} P")
    if r["to"]:
        print(f"in {r['to']} NHL scoring: {r['adj_nhle']:.1f} P (era factor {r['era_factor']:.3f})")
    if r["gp"]:
        print(f"per {args.per:g} games: {r[f'per{args.per:g}']:.1f} P")


def cmd_nhle_chart(args):
    df = _chart.series(args.leagues or None, ref=args.ref)
    t = _chart.wide(df, "factor" if args.raw else "nhle")
    which = "same-season NHL" if args.raw else f"{data.season_label(df.attrs['ref'])} NHL scoring"
    print(f"NHLe (NHL points per league point), {which}:")
    with pd.option_context("display.max_rows", None, "display.width", 250, "display.float_format", "{:.3f}".format):
        print(t.to_string())
    if df.stepped.any():
        print(f"from {data.season_label(_nhle.RULE_CHANGE)} the NCAA/CHL values include the rule-change step")
    if not args.no_html:
        print(f"chart -> {_chart.write(args.leagues or None, ref=args.ref, out=args.out)}")


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

    bn = sub.add_parser("build-nhle", help="fetch the season-by-season NHLe table (data/nhle_factors.csv)")
    bn.add_argument("--source", help="a local factors_by_season.csv or URL (default: the NHLe repo)")
    bn.set_defaults(func=cmd_build_nhle)

    nt = sub.add_parser("nhle-table", help="print NHLe factors by league and season")
    nt.add_argument("leagues", nargs="*", help="league keys (ohl, ncaa, shl...); default all")
    nt.add_argument("--from", dest="start", type=_season)
    nt.add_argument("--to", dest="end", type=_season)
    nt.set_defaults(func=cmd_nhle_table)

    n = sub.add_parser("nhle", help="a league season's points as NHL points (optionally in another NHL season's scoring)")
    n.add_argument("league")
    n.add_argument("season", type=_season)
    n.add_argument("-p", "--points", type=float, required=True)
    n.add_argument("--gp", type=float)
    n.add_argument("--to", type=_season, help="restate in this NHL season's scoring")
    n.add_argument("--per", type=float, default=82, help="games to scale to with --gp (default 82)")
    n.set_defaults(func=cmd_nhle)

    c = sub.add_parser("nhle-chart", help="era-adjusted NHLe by league over time: table + interactive HTML chart")
    c.add_argument("leagues", nargs="*", help=f"league keys; 'chl' = OHL+WHL+QMJHL (default: {' '.join(_chart.DEFAULT_LEAGUES)})")
    c.add_argument("--ref", type=_season, help="NHL season whose scoring everything is restated in (default: latest complete)")
    c.add_argument("--raw", action="store_true", help="print the same-season factors instead")
    c.add_argument("--out", help=f"HTML path (default: {_chart.OUT.relative_to(data.ROOT)})")
    c.add_argument("--no-html", action="store_true", help="table only")
    c.set_defaults(func=cmd_nhle_chart)

    args = p.parse_args(argv)
    args.func(args)
