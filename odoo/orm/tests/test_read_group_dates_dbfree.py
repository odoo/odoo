import pytest

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env
from odoo.tools import get_lang

_MOD = "test_read_group_dates_dbfree"

# read_group is the ORM's formatted API (format.py, fill.py); deprecated in
# favour of web's formatted_read_group, still the entry point these pin
pytestmark = pytest.mark.filterwarnings(
    "ignore:Call to deprecated method:DeprecationWarning"
)


class Visit(models.Model):
    _name = "rgd.visit"
    _module = _MOD
    _description = "visit"
    _log_access = False

    day = fields.Date()
    visits = fields.Integer()


@pytest.fixture
def env():
    with model_test_env(Visit) as env:
        env["rgd.visit"].create(
            [
                {"day": "2026-01-15", "visits": 5},
                {"day": "2026-03-02", "visits": 1},
                {"day": "2026-03-20", "visits": 2},
                {"day": False, "visits": 9},
            ]
        )
        yield env


def test_get_lang_answers_en_us_formats_without_a_language_table(env):
    lang = get_lang(env)
    assert lang.code == "en_US"
    assert lang.week_start == "7"
    assert lang.date_format == "%m/%d/%Y"
    assert bool(lang)
    assert get_lang(env.registry.locale and env, "fr_FR").code == "en_US"


def test_month_groups_carry_labels_domains_and_ranges(env):
    rows = env["rgd.visit"].read_group([], ["visits:sum"], ["day:month"], lazy=False)
    assert [(r["day:month"], r["visits"]) for r in rows] == [
        ("January 2026", 5),
        ("March 2026", 3),
        (False, 9),
    ]
    assert rows[0]["__range"] == {
        "day:month": {"from": "2026-01-01", "to": "2026-02-01"}
    }
    assert rows[0]["__domain"] == [
        "&",
        ("day", ">=", "2026-01-01"),
        ("day", "<", "2026-02-01"),
    ]
    assert rows[2]["__domain"] == [("day", "=", False)]


def test_fill_temporal_inserts_the_empty_month(env):
    rows = (
        env["rgd.visit"]
        .with_context(fill_temporal=True)
        .read_group([], ["visits:sum"], ["day:month"], lazy=False)
    )
    assert [r["day:month"] for r in rows] == [
        "January 2026",
        "February 2026",
        "March 2026",
        False,
    ]
    assert rows[1]["__count"] == 0 and rows[1]["visits"] is False


def test_weeks_start_on_the_language_first_week_day(env):
    # en_US starts its week on Sunday: January 15 2026, a Thursday, belongs
    # to the week of Sunday January 11, as date_trunc shifted by week_start
    rows = env["rgd.visit"].read_group([], ["visits:sum"], ["day:week"], lazy=False)
    assert rows[0]["__range"] == {
        "day:week": {"from": "2026-01-11", "to": "2026-01-18"}
    }
    assert [r["day:week"] for r in rows][:3] == ["W3 2026", "W10 2026", "W12 2026"]
    assert rows[1]["__range"]["day:week"]["from"] == "2026-03-01"


def test_quarters_and_years(env):
    rows = env["rgd.visit"].read_group([], ["visits:sum"], ["day:quarter"], lazy=False)
    assert [(r["day:quarter"], r["visits"]) for r in rows] == [
        ("Q1 2026", 8),
        (False, 9),
    ]
    rows = env["rgd.visit"]._read_group([], ["day:year"], ["visits:sum"])
    assert [(str(r[0]), r[1]) for r in rows] == [("2026-01-01", 8), ("False", 9)]


class Event(models.Model):
    _name = "rgd.event"
    _module = _MOD
    _description = "event at an instant"
    _log_access = False

    at = fields.Datetime()


def test_a_datetime_groups_by_the_context_timezone_like_timezone_in_sql():
    with model_test_env(Event) as env:
        env["rgd.event"].create(
            [
                {"at": "2026-01-15 23:30:00"},
                {"at": "2026-01-16 03:00:00"},
                {"at": "2026-01-16 12:00:00"},
            ]
        )
        Event_ = env["rgd.event"]
        assert [
            (str(r[0]), r[1]) for r in Event_._read_group([], ["at:day"], ["__count"])
        ] == [
            ("2026-01-15 00:00:00", 1),
            ("2026-01-16 00:00:00", 2),
        ]
        local = Event_.with_context(tz="America/Mexico_City")
        assert [
            (str(r[0]), r[1]) for r in local._read_group([], ["at:day"], ["__count"])
        ] == [
            ("2026-01-15 00:00:00", 2),
            ("2026-01-16 00:00:00", 1),
        ]
        assert [str(r[0]) for r in local._read_group([], ["at:hour"], ["__count"])] == [
            "2026-01-15 17:00:00",
            "2026-01-15 21:00:00",
            "2026-01-16 06:00:00",
        ]
        # a zone the server would not know groups in UTC, as the SQL path does
        unknown = Event_.with_context(tz="Mars/Olympus")
        assert [r[1] for r in unknown._read_group([], ["at:day"], ["__count"])] == [
            1,
            2,
        ]
        assert "America/Mexico_City" in env.backend.timezone_names(env)


class Tag(models.Model):
    _name = "rgd.tag"
    _module = _MOD
    _description = "tag"
    _order = "name"
    _log_access = False

    name = fields.Char()
    active = fields.Boolean(default=True)


class Post(models.Model):
    _name = "rgd.post"
    _module = _MOD
    _description = "post"
    _log_access = False

    name = fields.Char()
    tag_ids = fields.Many2many("rgd.tag")
    day = fields.Date()


def test_a_many2many_groupby_yields_one_row_per_relation_pair():
    with model_test_env(Tag, Post) as env:
        zeta, alpha, gone = env["rgd.tag"].create(
            [{"name": "zeta"}, {"name": "alpha"}, {"name": "gone", "active": False}]
        )
        Post_ = env["rgd.post"]
        Post_.create(
            [
                {"name": "p1", "tag_ids": [(6, 0, [zeta.id, alpha.id, gone.id])]},
                {"name": "p2", "tag_ids": [(6, 0, [zeta.id])]},
                {"name": "p3"},
            ]
        )
        rows = Post_._read_group([], ["tag_ids"], ["__count", "name:array_agg"])
        assert [(row[0].name if row[0] else None, row[1]) for row in rows] == [
            ("zeta", 2),
            ("alpha", 1),
            (None, 1),
        ]
        # an inactive tag is outside the field's comodel domain, as the join's subselect leaves it
        assert not any(row[0] == gone for row in rows)
        # an explicit many2many term sorts by the relation column, the ids, not
        # by the comodel's _order as a many2one term would
        rows = Post_._read_group([], ["tag_ids"], ["__count"], order="tag_ids desc")
        assert [row[0].name if row[0] else None for row in rows] == [
            None,
            "alpha",
            "zeta",
        ]


def test_number_granularities_answer_date_part_and_day_of_week_sorts_from_the_week_start():
    with model_test_env(Tag, Post) as env:
        Post_ = env["rgd.post"]
        # Thursday, Monday, Sunday, and no day
        Post_.create(
            [
                {"day": "2026-01-15"},
                {"day": "2026-03-02"},
                {"day": "2026-03-01"},
                {},
            ]
        )
        parts = {
            "day:month_number": [1, 3, 3, False],
            "day:quarter_number": [1, 1, 1, False],
            "day:iso_week_number": [3, 10, 9, False],
            "day:day_of_year": [15, 61, 60, False],
            "day:day_of_month": [15, 2, 1, False],
            "day:year_number": [2026, 2026, 2026, False],
        }
        for spec, expected in parts.items():
            rows = Post_._read_group([], [spec], ["__count"])
            got = {row[0]: row[1] for row in rows}
            wanted: dict = {}
            for value in expected:
                wanted[value] = wanted.get(value, 0) + 1
            assert got == wanted, spec
        # PostgreSQL's dow: Sunday 0 .. Saturday 6; en_US starts its week on
        # Sunday, so the default order runs Sunday, Monday, Thursday, then NULL
        rows = Post_._read_group([], ["day:day_of_week"], ["__count"])
        assert [row[0] for row in rows] == [0, 1, 4, False]
