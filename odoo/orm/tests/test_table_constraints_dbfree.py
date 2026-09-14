import pytest
from psycopg.errors import NotNullViolation, UniqueViolation

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
