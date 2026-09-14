import pytest

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_read_group_order_dbfree"


class Team(models.Model):
    _name = "rgo.team"
    _module = _MOD
    _description = "team, displayed by name"
    _order = "name"
    _log_access = False

    name = fields.Char()


class Score(models.Model):
    _name = "rgo.score"
    _module = _MOD
    _description = "score"
    _log_access = False

    team_id = fields.Many2one("rgo.team")
    points = fields.Integer()
    played = fields.Date()
    home = fields.Boolean()


@pytest.fixture
def env():
    with model_test_env(Team, Score) as env:
        zulu, alpha = env["rgo.team"].create([{"name": "zulu"}, {"name": "alpha"}])
        env["rgo.score"].create(
            [
                {"team_id": zulu.id, "points": 5, "played": "2026-01-01", "home": True},
                {"team_id": zulu.id, "points": 1, "played": "2026-02-01"},
                {"team_id": alpha.id, "points": 2, "played": "2026-02-01"},
                {"team_id": False, "points": 9, "played": False},
            ]
        )
        yield env


def _names(rows):
    return [row[0].name if row[0] else None for row in rows]


def test_the_default_order_follows_the_groupby_values_nulls_last(env):
    rows = env["rgo.score"]._read_group([], ["team_id"], ["points:sum"])
    assert _names(rows) == ["zulu", "alpha", None]
    assert [row[1] for row in rows] == [6, 2, 9]


def test_a_many2one_term_orders_by_the_comodel_order(env):
    rows = env["rgo.score"]._read_group(
        [], ["team_id"], ["points:sum"], order="team_id"
    )
    assert _names(rows) == ["alpha", "zulu", None]
    rows = env["rgo.score"]._read_group(
        [], ["team_id"], ["points:sum"], order="team_id desc"
    )
    assert _names(rows) == [None, "zulu", "alpha"]


def test_an_aggregate_term_orders_with_explicit_nulls(env):
    rows = env["rgo.score"]._read_group(
        [], ["team_id"], ["points:sum"], order="points:sum desc"
    )
    assert [row[1] for row in rows] == [9, 6, 2]
    rows = env["rgo.score"]._read_group(
        [], ["played:month"], ["__count"], order="played:month desc nulls last"
    )
    assert not rows[-1][0]
    assert [row[1] for row in rows] == [2, 1, 1]


def test_a_term_that_is_neither_groupby_nor_aggregate_is_refused(env):
    with pytest.raises(ValueError, match="not a valid aggregate nor valid groupby"):
        env["rgo.score"]._read_group([], ["team_id"], ["__count"], order="points")


def test_an_aggregate_outside_the_selection_orders_without_being_returned(env):
    rows = env["rgo.score"]._read_group(
        [], ["team_id"], ["__count"], order="points:sum desc, team_id"
    )
    assert [(row[0].name or False, row[1]) for row in rows] == [
        (False, 1),
        ("zulu", 2),
        ("alpha", 1),
    ]
    assert all(len(row) == 2 for row in rows)


def test_having_filters_groups_on_aggregates_and_groupby_values(env):
    Score = env["rgo.score"]
    rows = Score._read_group(
        [], ["team_id"], ["points:sum"], having=[("points:sum", ">", 3)]
    )
    assert sorted(row[1] for row in rows) == [6, 9]
    rows = Score._read_group(
        [],
        ["team_id"],
        ["points:sum", "__count"],
        having=["|", ("__count", "=", 2), ("points:sum", "in", [9])],
    )
    assert sorted(row[1] for row in rows) == [6, 9]
    rows = Score._read_group(
        [], ["team_id"], ["points:sum"], having=["!", ("points:sum", "<", 6)]
    )
    assert sorted(row[1] for row in rows) == [6, 9]
    # a NULL group value compares to nothing, as it does in SQL
    # the SQL path admits aggregates only in HAVING; the ORM refuses the rest first
    with pytest.raises(ValueError, match="Aggregate method is mandatory"):
        Score._read_group([], ["team_id"], ["__count"], having=[("points", ">", 1)])


def test_a_many2one_path_groups_by_the_comodel_field(env):
    rows = env["rgo.score"]._read_group([], ["team_id.name"], ["points:sum"])
    assert [(row[0], row[1]) for row in rows] == [("alpha", 2), ("zulu", 6), (False, 9)]
    rows = env["rgo.score"]._read_group(
        [], ["team_id.name"], ["__count"], order="team_id.name desc"
    )
    assert [row[0] for row in rows] == [False, "zulu", "alpha"]


def test_a_never_written_boolean_aggregates_as_false(env):
    # zulu's second score never wrote home: False to the ORM, as it is to a
    # domain and to a groupby, and to the SQL aggregates through COALESCE
    rows = env["rgo.score"]._read_group(
        [("team_id.name", "=", "zulu")],
        [],
        ["home:bool_and", "home:bool_or", "home:count", "home:array_agg"],
    )
    assert rows == [(False, True, 2, [True, False])]
    rows = env["rgo.score"]._read_group([], ["home"], ["__count"])
    assert rows == [(False, 3), (True, 1)]


class Ledger(models.Model):
    _name = "rgo.ledger"
    _module = _MOD
    _description = "amounts on numeric and double precision columns"
    _log_access = False

    amount = fields.Float(digits=(16, 2))
    ratio = fields.Float()


def test_a_sum_on_a_numeric_column_is_exact_as_in_sql():
    with model_test_env(Ledger) as env:
        Ledger_ = env["rgo.ledger"]
        Ledger_.create([{"amount": v, "ratio": v} for v in (0.1, 0.2)])
        [(amount, ratio, mean)] = Ledger_._read_group(
            [], [], ["amount:sum", "ratio:sum", "amount:avg"]
        )
        # numeric(16, 2) sums the decimals the floats spell; float8 sums doubles
        assert amount == 0.3
        assert ratio == 0.1 + 0.2 != 0.3
        assert mean == 0.15
