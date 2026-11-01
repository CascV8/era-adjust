import pandas as pd
import pytest

from era_adjust import factors

TOTALS = pd.DataFrame({
    "season":       [2002, 2003, 2005, 2006],   # 2004-05 not played
    "teams":        [30, 30, 30, 30],
    "team_games":   [2460, 2460, 2460, 2460],
    "goals":        [6000, 6150, 7380, 6765],
    "skater_goals": [6000, 6150, 7380, 6765],
    "assists":      [10200, 10455, 12546, 11500],
    "max_gp":       [82, 82, 82, 82],
})


def test_previous_season_skips_the_lockout():
    df = factors.compute(TOTALS)
    assert df.loc[df.season == 2005, "prev_season"].item() == 2003


def test_factor_vs_prev_is_gpg_ratio():
    df = factors.compute(TOTALS).set_index("season")
    assert df.loc[2005, "goal_factor_vs_prev"] == pytest.approx(6150 / 7380)
    assert df.loc[2005, "gpg_change_pct"] == pytest.approx((7380 / 6150 - 1) * 100)
    assert pd.isna(df.loc[2002, "goal_factor_vs_prev"])


def test_chained_factors_equal_direct_ratio():
    df = factors.compute(TOTALS, ref=2006).set_index("season")
    for s in df.index:
        assert df.loc[s, "goal_factor_to_ref"] == pytest.approx(df.loc[2006, "gpg"] / df.loc[s, "gpg"])
        assert df.loc[s, "assist_factor_to_ref"] == pytest.approx(df.loc[2006, "apg"] / df.loc[s, "apg"])
    assert df.loc[2006, "goal_factor_to_ref"] == pytest.approx(1.0)


def test_default_ref_skips_partial_season():
    df = factors.compute(TOTALS, current=2006)
    assert df.attrs["ref"] == 2005
    assert df.loc[df.season == 2006, "partial"].item()


def test_unknown_ref():
    with pytest.raises(ValueError):
        factors.compute(TOTALS, ref=2004)
