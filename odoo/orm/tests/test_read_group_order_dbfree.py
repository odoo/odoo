import pytest

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_read_group_order_dbfree"


class Team(models.Model):
    _name = "rg.team"
    _module = _MOD
    _description = "team, displayed by name"
    _order = "name"
    _log_access = False

    name = fields.Char()


class Score(models.Model):
    _name = "rg.score"
    _module = _MOD
    _description = "score"
    _log_access = False

    team_id = fields.Many2one("rg.team")
    points = fields.Integer()
    played = fields.Date()


@pytest.fixture
def env():
    with model_test_env(Team, Score) as env:
        zulu, alpha = env["rg.team"].create([{"name": "zulu"}, {"name": "alpha"}])
        env["rg.score"].create(
            [
                {"team_id": zulu.id, "points": 5, "played": "2026-01-01"},
                {"team_id": zulu.id, "points": 1, "played": "2026-02-01"},
                {"team_id": alpha.id, "points": 2, "played": "2026-02-01"},
                {"team_id": False, "points": 9, "played": False},
            ]
        )
        yield env


def _names(rows):
    return [row[0].name if row[0] else None for row in rows]


def test_the_default_order_follows_the_groupby_values_nulls_last(env):
    rows = env["rg.score"]._read_group([], ["team_id"], ["points:sum"])
    assert _names(rows) == ["zulu", "alpha", None]
    assert [row[1] for row in rows] == [6, 2, 9]


def test_a_many2one_term_orders_by_the_comodel_order(env):
    rows = env["rg.score"]._read_group([], ["team_id"], ["points:sum"], order="team_id")
    assert _names(rows) == ["alpha", "zulu", None]
    rows = env["rg.score"]._read_group(
        [], ["team_id"], ["points:sum"], order="team_id desc"
    )
    assert _names(rows) == [None, "zulu", "alpha"]


def test_an_aggregate_term_orders_with_explicit_nulls(env):
    rows = env["rg.score"]._read_group(
        [], ["team_id"], ["points:sum"], order="points:sum desc"
    )
    assert [row[1] for row in rows] == [9, 6, 2]
    rows = env["rg.score"]._read_group(
        [], ["played:month"], ["__count"], order="played:month desc nulls last"
    )
    assert not rows[-1][0]
    assert [row[1] for row in rows] == [2, 1, 1]


def test_a_term_that_is_neither_groupby_nor_aggregate_is_refused(env):
    with pytest.raises(ValueError, match="not a valid aggregate nor valid groupby"):
        env["rg.score"]._read_group([], ["team_id"], ["__count"], order="points")
