"""`index="unique"` is enforced by the database, so the DB-free tier must
enforce it too -- it is the only thing holding a One2one to one row, and a
twin that accepts a duplicate cannot catch the defect that breaks in SQL."""

import pytest
from psycopg.errors import UniqueViolation

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_memory_unique_index"


class Holder(models.Model):
    _name = "u.holder"
    _module = _MOD
    _description = "holder"
    _log_access = False

    name = fields.Char()


class Seat(models.Model):
    _name = "u.seat"
    _module = _MOD
    _description = "seat"
    _log_access = False

    name = fields.Char()
    holder_id = fields.Many2one("u.holder", index="unique")
    plain_id = fields.Many2one("u.holder")


def test_a_second_row_with_the_same_unique_value_is_refused():
    with model_test_env(Holder, Seat) as env:
        holder = env["u.holder"].create({"name": "h"})
        env["u.seat"].create({"name": "1", "holder_id": holder.id})
        env.flush_all()
        with pytest.raises(UniqueViolation):
            env["u.seat"].create({"name": "2", "holder_id": holder.id})
            env.flush_all()


def test_two_rows_of_one_batch_cannot_share_the_value_either():
    with model_test_env(Holder, Seat) as env:
        holder = env["u.holder"].create({"name": "h"})
        with pytest.raises(UniqueViolation):
            env["u.seat"].create(
                [
                    {"name": "1", "holder_id": holder.id},
                    {"name": "2", "holder_id": holder.id},
                ]
            )
            env.flush_all()


def test_null_is_not_a_duplicate_of_null():
    # the index carries WHERE col IS NOT NULL, and SQL never equates NULLs
    with model_test_env(Holder, Seat) as env:
        env["u.seat"].create([{"name": "1"}, {"name": "2"}, {"name": "3"}])
        env.flush_all()
        assert env["u.seat"].search_count([]) == 3


def test_a_column_without_the_attribute_is_not_unique():
    with model_test_env(Holder, Seat) as env:
        holder = env["u.holder"].create({"name": "h"})
        env["u.seat"].create(
            [
                {"name": "1", "plain_id": holder.id},
                {"name": "2", "plain_id": holder.id},
            ]
        )
        env.flush_all()
        assert env["u.seat"].search_count([("plain_id", "=", holder.id)]) == 2


def test_moving_the_value_to_another_row_is_allowed():
    with model_test_env(Holder, Seat) as env:
        holder = env["u.holder"].create({"name": "h"})
        first, second = env["u.seat"].create([{"name": "1"}, {"name": "2"}])
        first.holder_id = holder
        env.flush_all()
        first.holder_id = False
        second.holder_id = holder
        env.flush_all()
        assert second.holder_id == holder
        assert not first.holder_id
