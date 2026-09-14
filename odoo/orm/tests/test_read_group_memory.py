from datetime import date

import pytest

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


def test_the_unsupported_shapes_say_so():
    with model_test_env(Team, Score) as env:
        _seed(env)
        with pytest.raises(NotImplementedError, match="array aggregate"):
            env["rg.score"]._read_group(
                [], ["kind"], ["points:array_agg"], order="points:array_agg"
            )
