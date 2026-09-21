import pytest
from psycopg.errors import CheckViolation, NotNullViolation, UniqueViolation

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_table_constraints_dbfree"


class Slot(models.Model):
    _name = "tc.slot"
    _module = _MOD
    _description = "a slot with a required name and a unique pair"
    _log_access = False

    name = fields.Char(required=True)
    room = fields.Char()
    hour = fields.Integer()
    note = fields.Char()
    _room_hour_uniq = models.Constraint(
        "unique(room, hour)", "a room is booked once per hour"
    )


@pytest.fixture
def env():
    # a refused flush leaves the cache ahead of the rows, as on PostgreSQL
    # before the rollback: no cache-against-rows check at the end
    with model_test_env(Slot, check_cache=False) as env:
        yield env


def test_a_null_in_a_required_column_is_refused_as_the_table_would(env):
    with pytest.raises(NotNullViolation, match='column "name"'):
        env["tc.slot"].create({"name": False, "room": "a"})
    slot = env["tc.slot"].create({"name": "ok"})
    with pytest.raises(NotNullViolation):
        slot.name = False
        env.flush_all()


def test_a_duplicate_under_a_unique_constraint_is_refused(env):
    Slot_ = env["tc.slot"]
    Slot_.create({"name": "one", "room": "a", "hour": 9})
    with pytest.raises(UniqueViolation, match="tc_slot_room_hour_uniq"):
        Slot_.create({"name": "two", "room": "a", "hour": 9})
    with pytest.raises(UniqueViolation):
        Slot_.create(
            [
                {"name": "x", "room": "b", "hour": 1},
                {"name": "y", "room": "b", "hour": 1},
            ]
        )
    other = Slot_.create({"name": "three", "room": "a", "hour": 10})
    with pytest.raises(UniqueViolation):
        other.hour = 9
        env.flush_all()


def test_nulls_are_distinct_under_a_unique_constraint(env):
    Slot_ = env["tc.slot"]
    Slot_.create(
        [
            {"name": "n1", "room": False, "hour": 9},
            {"name": "n2", "room": False, "hour": 9},
        ]
    )
    assert Slot_.search_count([("hour", "=", 9)]) == 2
    booked = Slot_.create({"name": "b", "room": "c", "hour": 9})
    booked.note = "a write on another column keeps its own row out of the check"
    env.flush_all()


class Reading(models.Model):
    _name = "tc.reading"
    _module = _MOD
    _description = "a reading whose colour and rating a CHECK bounds"
    _log_access = False

    name = fields.Char()
    color = fields.Integer()
    rating = fields.Integer()
    _color_positive = models.Constraint("CHECK(color >= 0)", "a colour is not negative")
    _rating_bounded = models.Constraint(
        "check(rating >= 0 and rating <= 5)", "a rating is 0 to 5"
    )


@pytest.fixture
def reading_env():
    with model_test_env(Reading, check_cache=False) as env:
        yield env


def test_a_row_a_check_constraint_refuses_is_refused_on_create(reading_env):
    with pytest.raises(CheckViolation, match="tc_reading_color_positive"):
        reading_env["tc.reading"].create({"name": "a", "color": -1})
    with pytest.raises(CheckViolation, match="tc_reading_rating_bounded"):
        reading_env["tc.reading"].create({"name": "b", "rating": 6})


def test_a_row_a_check_constraint_refuses_is_refused_on_write(reading_env):
    reading = reading_env["tc.reading"].create({"name": "a", "color": 1, "rating": 3})
    with pytest.raises(CheckViolation, match="tc_reading_color_positive"):
        reading.color = -1
        reading_env.flush_all()


def test_a_write_is_judged_against_the_columns_it_does_not_carry(reading_env):
    # the UPDATE carries `rating` alone, and the stored `color` supplies the
    # rest, so a row already inside both bounds stays acceptable
    reading = reading_env["tc.reading"].create({"name": "a", "color": 2, "rating": 1})
    reading.rating = 5
    reading_env.flush_all()
    assert reading.rating == 5


def test_a_row_both_checks_accept_is_stored(reading_env):
    reading = reading_env["tc.reading"].create({"name": "a", "color": 0, "rating": 5})
    reading_env.flush_all()
    assert (reading.color, reading.rating) == (0, 5)
