import numpy as np
import pytest

from era_adjust import main, nhle_chart
from era_adjust.adjust import table
from era_adjust.nhle_factors import factors


def test_reference_season_is_unchanged():
    df = nhle_chart.series(["khl"], ref=2025)
    row = df[df.season == 2025].iloc[0]
    assert row.era_factor == pytest.approx(1.0)
    assert row.nhle == pytest.approx(row.factor)


def test_era_factor_is_nhl_points_ratio():
    df = nhle_chart.series(["shl"], ref=2025).set_index("season")
    nhl = table()
    assert df.loc[2012, "era_factor"] == pytest.approx(nhl.loc[2025, "ppg"] / nhl.loc[2012, "ppg"])
    assert df.loc[2012, "nhle"] == pytest.approx(df.loc[2012, "factor"] * df.loc[2012, "era_factor"])


def test_chl_is_player_weighted_geometric_mean():
    chl = nhle_chart.series(["chl"]).set_index("season")
    f = factors()
    rows = f[(f.league.isin(["ohl", "whl", "qmjhl"])) & (f.season == 2018)]
    expected = np.exp((np.log(rows.factor) * rows.players).sum() / rows.players.sum())
    assert chl.loc[2018, "factor"] == pytest.approx(expected)
    assert rows.factor.min() <= chl.loc[2018, "factor"] <= rows.factor.max()


def test_rule_change_step_flagged_only_where_it_applies():
    df = nhle_chart.series()
    stepped = set(df[df.stepped].league)
    assert stepped == {"chl", "ncaa"}
    assert df[df.stepped].season.min() == 2025


def test_unknown_league():
    with pytest.raises(ValueError):
        nhle_chart.series(["xyz"])


def test_cli_writes_html(tmp_path, capsys):
    out = tmp_path / "chart.html"
    main(["nhle-chart", "--out", str(out)])
    text = out.read_text(encoding="utf-8")
    assert "<title>NHLe by League</title>" in text and '"name": "CHL"' in text
    assert "__" not in text.split("<script>")[0]   # every placeholder filled
    assert "KHL" in capsys.readouterr().out
