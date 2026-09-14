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
