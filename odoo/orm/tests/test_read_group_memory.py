from datetime import date

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env


class Team(models.Model):
    _name = "rg.team"
    _module = "odoo.addons.test_read_group_harness"
    _description = "Read group team"

    name = fields.Char()


class Score(models.Model):
    _name = "rg.score"
    _module = "odoo.addons.test_read_group_harness"
    _description = "Read group score"

    team_id = fields.Many2one("rg.team")
    kind = fields.Char()
    points = fields.Integer()
    day = fields.Date()
    won = fields.Boolean()
    tag_ids = fields.Many2many("rg.team")


def _seed(env):
    a = env["rg.team"].create({"name": "a"})
    b = env["rg.team"].create({"name": "b"})
    Score = env["rg.score"]
    Score.create(
        [
            {
                "team_id": a.id,
                "kind": "x",
                "points": 3,
                "day": "2026-01-05",
                "won": True,
            },
            {
                "team_id": a.id,
                "kind": "y",
                "points": 5,
                "day": "2026-01-20",
                "won": False,
            },
            {
                "team_id": b.id,
                "kind": "x",
                "points": 7,
                "day": "2026-02-02",
                "won": True,
            },
            {"team_id": False, "kind": "", "points": 1, "day": False, "won": False},
        ]
    )
    return a, b


def test_groups_by_a_many2one_with_standard_aggregates():
    with model_test_env(Team, Score) as env:
        a, b = _seed(env)
        rows = env["rg.score"]._read_group(
            [], ["team_id"], ["points:sum", "__count", "won:bool_and", "id:recordset"]
        )
        assert [(row[0], row[1], row[2], row[3]) for row in rows] == [
            (a, 8, 2, False),
            (b, 7, 1, True),
            (env["rg.team"], 1, 1, False),
        ]
        assert rows[0][4]._name == "rg.score" and len(rows[0][4]) == 2


def test_groups_by_text_and_month_and_pages_the_groups():
    with model_test_env(Team, Score) as env:
        _seed(env)
        Scores = env["rg.score"]
        by_kind = Scores._read_group([], ["kind"], ["points:max", "points:count"])
        assert by_kind == [("x", 7, 2), ("y", 5, 1), (False, 1, 1)]
        by_month = Scores._read_group(
            [("day", "!=", False)], ["day:month"], ["points:avg"]
        )
        assert by_month == [(date(2026, 1, 1), 4.0), (date(2026, 2, 1), 7.0)]
        assert Scores._read_group([], ["kind"], ["__count"], limit=1, offset=1) == [
            ("y", 1)
        ]


def test_an_order_by_an_array_aggregate_compares_arrays_as_postgresql_does():
    # element by element, a shorter prefix first; pinned against PostgreSQL by
    # test_read_group's TestReadGroupBackendWalk
    with model_test_env(Team, Score) as env:
        _seed(env)
        rows = env["rg.score"]._read_group(
            [], ["kind"], ["points:array_agg"], order="points:array_agg"
        )
        assert rows == [(False, [1]), ("x", [3, 7]), ("y", [5])]
        rows = env["rg.score"]._read_group(
            [], ["kind"], ["points:array_agg"], order="points:array_agg desc"
        )
        assert rows == [("y", [5]), ("x", [3, 7]), (False, [1])]


def test_aggregates_skip_null_numeric_cells_like_sql():
    # count(col)/avg(col) ignore NULL cells in SQL; the cache reads a stored
    # NULL integer as 0, so the readers must consult the stored cell
    with model_test_env(Team, Score) as env:
        _seed(env)
        env["rg.score"].create({"kind": "x"})  # points is NULL
        rows = env["rg.score"]._read_group(
            [("kind", "=", "x")],
            [],
            ["points:count", "points:avg", "points:sum", "points:min", "__count"],
        )
        assert rows == [(2, 5.0, 10, 3, 3)]
