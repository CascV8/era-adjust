import pytest

from era_adjust import adjust, main


def test_adjust_defaults_to_previous_season():
    r = adjust(2005, goals=50, assists=50)
    assert r["to"] == "2003-04"
    assert r["adj_goals"] < 50  # 2005-06 scored far more than 2003-04


def test_adjust_to_same_season_is_identity():
    r = adjust(2025, goals=40, assists=30, to=2025)
    assert r["adj_goals"] == pytest.approx(40)
    assert r["adj_assists"] == pytest.approx(30)


def test_schedule_scaling():
    r = adjust(1981, goals=92, assists=120, gp=80, to=2025, schedule=True)
    assert r["schedule_factor"] == pytest.approx(82 / 80)
    assert r["gp"] == pytest.approx(82)


def test_lockout_season_rejected():
    with pytest.raises(ValueError):
        adjust(2004, goals=10)


def test_cli_runs(capsys):
    main(["adjust", "1981-82", "-g", "92", "-a", "120", "--to", "2025"])
    assert "2025-26 terms" in capsys.readouterr().out
