"""Era-adjusted NHLe by league over time, as a table and an interactive HTML chart.

A league's NHLe factor turns its points into NHL points of the *same* season. The era-adjusted
value restates them in the reference NHL season's scoring:

    adjusted = factor(league, season) x PPG(NHL, ref) / PPG(NHL, season)

where PPG is NHL points per team-game (``era_factors.csv``). "chl" is the OHL, WHL and QMJHL
together: the geometric mean of their factors, weighted by each league's crossover players.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .adjust import table as nhl_table
from .data import ROOT, season_label
from .nhle_factors import RULE_CHANGE, factors

DEFAULT_LEAGUES = ["chl", "liiga", "khl", "ncaa", "shl", "ushl"]
GROUPS = {"chl": ["ohl", "whl", "qmjhl"]}
NAMES = {"chl": "CHL", "liiga": "Liiga", "khl": "KHL", "ncaa": "NCAA", "shl": "SHL", "ushl": "USHL",
         "ohl": "OHL", "whl": "WHL", "qmjhl": "QMJHL", "ahl": "AHL", "nl": "NL", "del": "DEL",
         "allsvenskan": "Allsvenskan", "mhl": "MHL", "vhl": "VHL", "ntdp": "NTDP"}
STEPPED = {"ncaa", "ohl", "whl", "qmjhl", "chl"}   # leagues with the 2025-26 rule-change step
OUT = ROOT / "reports" / "nhle_by_season.html"


def name(league: str) -> str:
    return NAMES.get(league, league.upper())


def _league_rows(league: str) -> pd.DataFrame:
    df = factors()
    members = GROUPS.get(league, [league])
    rows = df[df.league.isin(members)]
    missing = set(members) - set(rows.league)
    if missing:
        known = ", ".join(sorted(set(df.league) | set(GROUPS)))
        raise ValueError(f"no NHLe factors for {', '.join(sorted(missing))}; leagues: {known}")
    if len(members) == 1:
        return rows[["season", "factor", "players"]]
    rows = rows.assign(logf=np.log(rows.factor) * rows.players)
    g = rows.groupby("season").agg(logf=("logf", "sum"), players=("players", "sum")).reset_index()
    g["factor"] = np.exp(g.logf / g.players)
    return g[["season", "factor", "players"]]


def series(leagues=None, ref: int | None = None) -> pd.DataFrame:
    """One row per league and season: raw NHLe factor, era factor and era-adjusted NHLe."""
    leagues = [l.lower() for l in (leagues or DEFAULT_LEAGUES)]
    nhl = nhl_table()
    ref = ref if ref is not None else int(nhl.index[~nhl["partial"].astype(bool)].max())
    if ref not in nhl.index:
        raise ValueError(f"no NHL season {season_label(ref)}")
    frames = []
    for league in leagues:
        rows = _league_rows(league).copy()
        missing = sorted(set(rows.season) - set(nhl.index))
        if missing:
            raise ValueError(f"no NHL scoring for {', '.join(map(season_label, missing))}")
        rows["era_factor"] = nhl.loc[ref, "ppg"] / nhl.loc[rows.season, "ppg"].to_numpy()
        rows["nhle"] = rows.factor * rows.era_factor
        rows["league"] = league
        rows["stepped"] = rows.season.ge(RULE_CHANGE) & (league in STEPPED)
        frames.append(rows)
    out = pd.concat(frames, ignore_index=True)
    out["label"] = out.season.map(season_label)
    out.attrs["ref"] = ref
    return out[["league", "season", "label", "factor", "era_factor", "nhle", "players", "stepped"]]


def wide(df: pd.DataFrame, column: str = "nhle") -> pd.DataFrame:
    """Seasons down, leagues across, in the order the leagues were asked for."""
    order = list(dict.fromkeys(df.league))
    t = df.pivot(index="label", columns="league", values=column)[order]
    t.columns = [name(c) for c in order]
    return t


def html(df: pd.DataFrame) -> str:
    ref = df.attrs["ref"]
    payload = {
        "ref": season_label(ref),
        "seasons": sorted(df.label.unique()),
        "ruleChange": season_label(RULE_CHANGE),
        "leagues": [
            {"key": l, "name": name(l),
             "adj": [round(v, 4) for v in g.sort_values("season").nhle],
             "raw": [round(v, 4) for v in g.sort_values("season").factor],
             "stepped": list(g.sort_values("season").stepped.astype(bool))}
            for l, g in df.groupby("league", sort=False)
        ],
    }
    span = f"{payload['seasons'][0]} to {payload['seasons'][-1]}"
    return (TEMPLATE.replace("__DATA__", json.dumps(payload)).replace("__REF__", payload["ref"])
            .replace("__RANGE__", span))


def write(leagues=None, ref: int | None = None, out: Path | str | None = None) -> Path:
    df = series(leagues, ref)
    out = Path(out) if out else OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html(df), encoding="utf-8")
    return out


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NHLe by League</title>
<style>
:root {
  --surface-0: #f5f5f3; --surface-1: #fcfcfb; --border: #e3e2dd;
  --text-primary: #1d1d1b; --text-secondary: #5c5b55; --text-muted: #85847c;
  --grid: #ebeae6; --axis: #c9c8c1; --accent: #2a78d6;
  --s1: #2a78d6; --s2: #eb6834; --s3: #1baf7a; --s4: #eda100; --s5: #e87ba4; --s6: #008300;
  --s7: #6250d6; --s8: #e34948;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --surface-0: #121211; --surface-1: #1a1a19; --border: #2e2e2c;
    --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #8f8e85;
    --grid: #262624; --axis: #45443f; --accent: #3987e5;
    --s1: #3987e5; --s2: #d95926; --s3: #199e70; --s4: #c98500; --s5: #d55181; --s6: #008300;
    --s7: #9085e9; --s8: #e66767;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface-0: #121211; --surface-1: #1a1a19; --border: #2e2e2c;
  --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #8f8e85;
  --grid: #262624; --axis: #45443f; --accent: #3987e5;
  --s1: #3987e5; --s2: #d95926; --s3: #199e70; --s4: #c98500; --s5: #d55181; --s6: #008300;
  --s7: #9085e9; --s8: #e66767;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--surface-0); color: var(--text-primary);
  font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 980px; margin: 0 auto; padding: 32px 16px 48px; }
h1 { font-size: 22px; margin: 0 0 4px; letter-spacing: -0.01em; }
.sub { color: var(--text-secondary); margin: 0 0 20px; max-width: 70ch; }
.card { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }
.controls { display: flex; flex-wrap: wrap; gap: 12px 20px; align-items: center; margin-bottom: 12px; }
.seg { display: inline-flex; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.seg button { font: inherit; font-size: 13px; padding: 6px 12px; border: 0; background: transparent;
  color: var(--text-secondary); cursor: pointer; }
.seg button[aria-pressed="true"] { background: var(--accent); color: #fff; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 13px; color: var(--text-secondary); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.legend i { width: 14px; height: 3px; border-radius: 2px; display: inline-block; }
.chart { position: relative; }
svg { display: block; width: 100%; height: auto; overflow: visible; }
.tick { fill: var(--text-muted); font-size: 11px; }
.endlabel { fill: var(--text-primary); font-size: 12px; font-weight: 600; }
.tip { position: absolute; pointer-events: none; background: var(--surface-1); border: 1px solid var(--border);
  border-radius: 8px; padding: 8px 10px; font-size: 12px; box-shadow: 0 4px 16px rgb(0 0 0 / 0.12);
  min-width: 150px; display: none; z-index: 2; }
.tip b { display: block; margin-bottom: 4px; }
.tip div { display: flex; justify-content: space-between; gap: 12px; align-items: center; }
.tip i { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }
.tip .v { font-variant-numeric: tabular-nums; }
.note { color: var(--text-muted); font-size: 12px; margin: 12px 0 0; }
details { margin-top: 20px; }
summary { cursor: pointer; color: var(--text-secondary); }
.tablewrap { overflow-x: auto; margin-top: 10px; }
table { border-collapse: collapse; font-size: 12px; font-variant-numeric: tabular-nums; width: 100%; }
th, td { padding: 4px 8px; text-align: right; border-bottom: 1px solid var(--border); white-space: nowrap; }
th:first-child, td:first-child { text-align: left; }
th { color: var(--text-secondary); font-weight: 600; }
</style>
</head>
<body>
<main>
  <h1>NHLe by league, <span style="white-space:nowrap">__RANGE__</span></h1>
  <p class="sub">NHL points per league point, season by season, from the NHLe network.
    <strong>Era-adjusted</strong> restates every season in __REF__ NHL scoring (× the NHL's points per
    team-game ratio); <strong>Same season</strong> is the raw factor in that season's own NHL.</p>
  <div class="card">
    <div class="controls">
      <div class="seg" role="group" aria-label="Scale">
        <button type="button" data-mode="adj" aria-pressed="true">Era-adjusted</button>
        <button type="button" data-mode="raw" aria-pressed="false">Same season</button>
      </div>
      <div class="legend" id="legend"></div>
    </div>
    <div class="chart" id="chart"><div class="tip" id="tip"></div></div>
    <p class="note">CHL = OHL, WHL and QMJHL combined (geometric mean weighted by crossover players).
      Hollow points: from __RULE__ the NCAA and CHL factors include a step for the rule change letting
      CHL players keep NCAA eligibility — one season of data so far, so treat them as provisional.</p>
  </div>
  <details>
    <summary>Table view</summary>
    <div class="tablewrap"><table id="table"></table></div>
  </details>
</main>
<script>
const D = __DATA__;
const N = D.seasons.length;
let mode = "adj";
const chart = document.getElementById("chart"), tip = document.getElementById("tip");
const color = i => `var(--s${i + 1})`;
const short = s => s.slice(2);  // 2010-11 -> 10-11

document.getElementById("legend").innerHTML = D.leagues.map((l, i) =>
  `<span><i style="background:${color(i)}"></i>${l.name}</span>`).join("");

function niceMax(v) {
  const step = v > 0.5 ? 0.1 : 0.05;
  return Math.ceil(v * 1.06 / step) * step;
}

function draw() {
  const W = Math.max(chart.clientWidth, 300), narrow = W < 560;
  const H = narrow ? 320 : 400;
  const m = { t: 12, r: narrow ? 52 : 64, b: 28, l: 40 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const vals = D.leagues.flatMap(l => l[mode]);
  const yMax = niceMax(Math.max(...vals));
  const x = i => m.l + (N === 1 ? iw / 2 : i * iw / (N - 1));
  const y = v => m.t + ih - v / yMax * ih;
  const step = yMax > 0.5 ? 0.1 : 0.05;
  let g = "";
  for (let v = 0; v <= yMax + 1e-9; v += step) {
    g += `<line x1="${m.l}" x2="${m.l + iw}" y1="${y(v)}" y2="${y(v)}" stroke="var(--grid)" stroke-width="1"/>`;
    g += `<text class="tick" x="${m.l - 6}" y="${y(v) + 4}" text-anchor="end">${v.toFixed(2)}</text>`;
  }
  g += `<line x1="${m.l}" x2="${m.l + iw}" y1="${y(0)}" y2="${y(0)}" stroke="var(--axis)" stroke-width="1"/>`;
  const every = narrow ? 3 : 1;
  D.seasons.forEach((s, i) => {
    if (i % every === 0 || i === N - 1)
      g += `<text class="tick" x="${x(i)}" y="${m.t + ih + 18}" text-anchor="middle">${short(s)}</text>`;
  });
  // rule-change marker
  const rc = D.seasons.indexOf(D.ruleChange);
  if (rc > 0) g += `<line x1="${x(rc)}" x2="${x(rc)}" y1="${m.t}" y2="${m.t + ih}" stroke="var(--axis)" stroke-dasharray="3 4"/>`;
  // lines
  D.leagues.forEach((l, li) => {
    const pts = l[mode].map((v, i) => `${x(i)},${y(v)}`).join(" ");
    g += `<polyline points="${pts}" fill="none" stroke="${color(li)}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`;
    l[mode].forEach((v, i) => {
      if (l.stepped[i]) g += `<circle cx="${x(i)}" cy="${y(v)}" r="4" fill="var(--surface-1)" stroke="${color(li)}" stroke-width="2"/>`;
    });
  });
  // end labels, nudged apart
  const ends = D.leagues.map((l, li) => ({ li, name: l.name, y: y(l[mode][N - 1]) })).sort((a, b) => a.y - b.y);
  const gap = 14;
  for (let k = 1; k < ends.length; k++) if (ends[k].y - ends[k - 1].y < gap) ends[k].y = ends[k - 1].y + gap;
  const over = ends.length ? ends[ends.length - 1].y - (m.t + ih) : 0;
  if (over > 0) ends.forEach(e => e.y -= over);
  ends.forEach(e => {
    g += `<text class="endlabel" x="${x(N - 1) + 10}" y="${e.y + 4}">${e.name}</text>`;
  });
  // hover layer
  g += `<line id="xh" x1="0" x2="0" y1="${m.t}" y2="${m.t + ih}" stroke="var(--text-muted)" stroke-width="1" visibility="hidden"/>`;
  g += `<g id="dots"></g>`;
  g += `<rect id="hit" x="${m.l - 10}" y="${m.t}" width="${iw + 20}" height="${ih}" fill="transparent"/>`;
  const old = chart.querySelector("svg"); if (old) old.remove();
  chart.insertAdjacentHTML("afterbegin",
    `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="NHLe by league and season">${g}</svg>`);
  const svg = chart.querySelector("svg"), xh = svg.querySelector("#xh"), dots = svg.querySelector("#dots");
  const hit = svg.querySelector("#hit");
  function at(ev) {
    const r = svg.getBoundingClientRect(), px = (ev.clientX - r.left) * W / r.width;
    const i = Math.max(0, Math.min(N - 1, Math.round((px - m.l) / iw * (N - 1))));
    xh.setAttribute("x1", x(i)); xh.setAttribute("x2", x(i)); xh.setAttribute("visibility", "visible");
    dots.innerHTML = D.leagues.map((l, li) =>
      `<circle cx="${x(i)}" cy="${y(l[mode][i])}" r="4.5" fill="${color(li)}" stroke="var(--surface-1)" stroke-width="2"/>`).join("");
    const rows = D.leagues.map((l, li) => ({ l, li, v: l[mode][i] })).sort((a, b) => b.v - a.v);
    tip.innerHTML = `<b>${D.seasons[i]}</b>` + rows.map(r =>
      `<div><span><i style="background:${color(r.li)}"></i>${r.l.name}${r.l.stepped[i] ? "*" : ""}</span><span class="v">${r.v.toFixed(3)}</span></div>`).join("")
      + (rows.some(r => r.l.stepped[i]) ? `<div style="color:var(--text-muted);margin-top:4px">* includes the rule-change step</div>` : "");
    tip.style.display = "block";
    const cx = x(i) * r.width / W, tw = tip.offsetWidth;
    tip.style.left = (cx + 14 + tw > r.width ? cx - tw - 14 : cx + 14) + "px";
    tip.style.top = "8px";
  }
  hit.addEventListener("pointermove", at);
  hit.addEventListener("pointerdown", at);
  hit.addEventListener("pointerleave", () => { tip.style.display = "none"; xh.setAttribute("visibility", "hidden"); dots.innerHTML = ""; });
}

function table() {
  const head = `<tr><th>Season</th>${D.leagues.map(l => `<th>${l.name}</th>`).join("")}</tr>`;
  const body = D.seasons.map((s, i) =>
    `<tr><td>${s}</td>${D.leagues.map(l => `<td>${l[mode][i].toFixed(3)}${l.stepped[i] ? "*" : ""}</td>`).join("")}</tr>`).join("");
  document.getElementById("table").innerHTML = head + body;
}

document.querySelectorAll(".seg button").forEach(b => b.addEventListener("click", () => {
  mode = b.dataset.mode;
  document.querySelectorAll(".seg button").forEach(o => o.setAttribute("aria-pressed", String(o === b)));
  draw(); table();
}));
new ResizeObserver(() => draw()).observe(chart);
draw(); table();
</script>
</body>
</html>
"""
TEMPLATE = TEMPLATE.replace("__RULE__", season_label(RULE_CHANGE))
