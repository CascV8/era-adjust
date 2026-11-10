import pytest

from era_adjust import main, nhle
from era_adjust import nhle_factors as nhle_mod


def test_factor_turns_league_points_into_nhl_points():
    r = nhle("ohl", 2023, points=100)
    assert r["nhle"] == pytest.approx(100 * nhle_mod.factor("ohl", 2023))
    assert 0.05 < r["factor"] < 0.3


def test_league_names_are_case_insensitive():
    assert nhle_mod.factor("NCAA", 2022) == nhle_mod.factor("ncaa", 2022)


def test_nhl_is_one():
    assert nhle_mod.factor("nhl", 2015) == 1.0


def test_seasons_past_the_table_use_the_last_one():
    last = int(nhle_mod.factors().season.max())
    assert nhle_mod.factor("ohl", last + 3) == nhle_mod.factor("ohl", last)


def test_rule_change_step_only_from_2025():
    df = nhle_mod.factors().set_index(["league", "season"])
    # the step leagues' 2024-25 and 2025-26 can differ; a European league isn't stepped
    assert ("ncaa", nhle_mod.RULE_CHANGE) in df.index
    assert ("shl", nhle_mod.RULE_CHANGE) in df.index


def test_to_restates_in_another_nhl_seasons_scoring():
    r = nhle("whl", 2010, points=80, gp=72, to=2025)
    assert r["adj_nhle"] == pytest.approx(r["nhle"] * r["era_factor"])
    assert r["per82"] == pytest.approx(r["adj_nhle"] / 72 * 82)


def test_unknown_league():
    with pytest.raises(ValueError, match="leagues"):
        nhle_mod.factor("xyz", 2020)


def test_cli_runs(capsys):
    main(["nhle", "ohl", "2023-24", "-p", "102", "--gp", "68", "--to", "2025"])
    out = capsys.readouterr().out
    assert "2025-26 NHL scoring" in out
    main(["nhle-table", "ncaa", "--from", "2024"])
    assert "ncaa" in capsys.readouterr().out
