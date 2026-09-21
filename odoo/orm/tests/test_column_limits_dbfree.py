"""What the driver and the column type refuse before a constraint is reached.

psycopg rejects a NUL in a text parameter and an int4 column rejects a value
outside its range, so a row carrying either never reaches the table. An
ORDER BY is refused by the same compiler the SQL backend uses, because which
non-stored fields it can compile is not a property this tier can restate.
"""

import pytest
from psycopg.errors import DataError, NumericValueOutOfRange

from odoo import api, fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_column_limits_dbfree"


class Group(models.Model):
    _name = "limit.group"
    _module = _MOD
    _description = "a group whose rank an item orders by"
    _log_access = False

    rank = fields.Integer()


class Item(models.Model):
    _name = "limit.item"
    _module = _MOD
    _description = "an item with an integer, a text and two unstored orders"
    _log_access = False

    code = fields.Char()
    body = fields.Text()
    tally = fields.Integer()
    amount = fields.Float(digits=(6, 2))
    group_id = fields.Many2one("limit.group")
    group_rank = fields.Integer(related="group_id.rank")
    label = fields.Char(compute="_compute_label")

    @api.depends("code")
    def _compute_label(self):
        for item in self:
            item.label = (item.code or "").upper()


@pytest.fixture
def env():
    with model_test_env(Group, Item, check_cache=False) as env:
        yield env


@pytest.mark.parametrize("value", [2**31, -(2**31) - 1, 2**40])
def test_an_integer_outside_int4_is_refused(env, value):
    with pytest.raises(NumericValueOutOfRange):
        env["limit.item"].create({"tally": value})


@pytest.mark.parametrize("value", [2**31 - 1, -(2**31), 0])
def test_an_integer_inside_int4_is_stored(env, value):
    assert env["limit.item"].create({"tally": value}).tally == value


def test_a_write_of_an_integer_outside_int4_is_refused(env):
    item = env["limit.item"].create({"tally": 1})
    with pytest.raises(NumericValueOutOfRange):
        item.tally = 2**31
        env.flush_all()


def test_a_numeric_column_carries_no_precision_and_overflows_at_nothing(env):
    # Float(digits=...) rounds in Python and its column is a bare `numeric`,
    # so a value wider than the digits is stored on both tiers
    item = env["limit.item"].create({"amount": 12345.67})
    env.flush_all()
    env.invalidate_all()
    assert item.amount == 12345.67


@pytest.mark.parametrize("fname", ["code", "body"])
def test_a_nul_byte_in_a_text_column_is_refused(env, fname):
    with pytest.raises(DataError, match="NUL"):
        env["limit.item"].create({fname: "a\x00b"})


def test_a_text_column_takes_every_other_character(env):
    item = env["limit.item"].create({"body": "a\tb\ncé\U0001f600"})
    env.flush_all()
    env.invalidate_all()
    assert item.body == "a\tb\ncé\U0001f600"


def test_an_order_by_a_non_stored_compute_is_refused(env):
    env["limit.item"].create([{"code": "b"}, {"code": "a"}])
    env.flush_all()
    with pytest.raises(ValueError, match="not stored"):
        env["limit.item"].search([], order="label")


def test_an_order_by_a_non_stored_related_is_allowed(env):
    # it compiles to a join, so the compiler accepts it and so must this
    groups = env["limit.group"].create([{"rank": 2}, {"rank": 1}])
    items = env["limit.item"].create(
        [{"group_id": groups[0].id}, {"group_id": groups[1].id}]
    )
    env.flush_all()
    assert env["limit.item"].search([], order="group_rank") == items[1] + items[0]


def test_an_order_by_a_stored_column_is_allowed(env):
    items = env["limit.item"].create([{"code": "b"}, {"code": "a"}])
    env.flush_all()
    assert env["limit.item"].search([], order="code") == items[1] + items[0]


def test_a_rolled_back_savepoint_does_not_give_an_id_back(env):
    # nextval is not transactional on PostgreSQL: a value the savepoint drew
    # is spent whether or not its row survives
    first = env["limit.item"].create({"code": "a"})
    env.flush_all()
    try:
        with env.cr.savepoint(flush=False):
            doomed = env["limit.item"].create({"code": "doomed"})
            env.flush_all()
            assert doomed.id == first.id + 1
            raise RuntimeError("roll it back")
    except RuntimeError:
        pass
    assert not env["limit.item"].browse(first.id + 1).exists()
    assert env["limit.item"].create({"code": "b"}).id == first.id + 2


def test_a_rolled_back_savepoint_does_give_the_rows_back(env):
    first = env["limit.item"].create({"code": "a"})
    env.flush_all()
    try:
        with env.cr.savepoint(flush=False):
            env["limit.item"].create({"code": "doomed"})
            env.flush_all()
            assert env["limit.item"].search_count([]) == 2
            raise RuntimeError("roll it back")
    except RuntimeError:
        pass
    assert env["limit.item"].search([]) == first
