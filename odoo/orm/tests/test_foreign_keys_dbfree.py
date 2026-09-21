"""The twin refuses a reference PostgreSQL refuses, and nothing more.

`update_db_foreign_key` declares a constraint for every stored many2one whose
comodel owns an ordinary table, and the DDL that would create it never runs on
this tier, so the declaration is derived from the fields instead.
"""

import pytest
from psycopg.errors import ForeignKeyViolation

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_foreign_keys_dbfree"


class Room(models.Model):
    _name = "fk.room"
    _module = _MOD
    _description = "a room a desk can stand in"
    _log_access = False

    name = fields.Char()


class Desk(models.Model):
    _name = "fk.desk"
    _module = _MOD
    _description = "a desk referencing a room and its own neighbour"
    _log_access = False

    name = fields.Char()
    room_id = fields.Many2one("fk.room", ondelete="restrict")
    neighbour_id = fields.Many2one("fk.desk")


@pytest.fixture
def env():
    # a refused flush leaves the cache ahead of the rows, as on PostgreSQL
    # before the rollback
    with model_test_env(Room, Desk, check_cache=False) as env:
        yield env


def test_a_reference_to_a_row_that_does_not_exist_is_refused(env):
    with pytest.raises(ForeignKeyViolation, match="room_id"):
        env["fk.desk"].create({"name": "d", "room_id": 987654})


def test_a_write_of_a_dangling_reference_is_refused(env):
    desk = env["fk.desk"].create({"name": "d"})
    with pytest.raises(ForeignKeyViolation, match="room_id"):
        desk.room_id = 987654
        env.flush_all()


def test_a_reference_to_a_row_that_exists_is_accepted(env):
    room = env["fk.room"].create({"name": "r"})
    desk = env["fk.desk"].create({"name": "d", "room_id": room.id})
    assert desk.room_id == room


def test_an_empty_reference_is_not_checked(env):
    desk = env["fk.desk"].create({"name": "d"})
    assert not desk.room_id
    desk.room_id = False
    env.flush_all()
    assert not desk.room_id


def test_a_row_may_reference_a_sibling_of_its_own_batch(env):
    # a multi-row INSERT checks its foreign keys once the statement ends
    first, second = env["fk.desk"].create([{"name": "a"}, {"name": "b"}])
    second.neighbour_id = first
    env.flush_all()
    assert second.neighbour_id == first


def test_the_acting_user_of_a_log_access_model_exists(env):
    class Logged(models.Model):
        _name = "fk.logged"
        _module = _MOD
        _description = "a model keeping its own create_uid"

        name = fields.Char()

    with model_test_env(Logged, check_cache=False) as logged_env:
        as_user = logged_env(user=2, su=False)
        record = as_user["fk.logged"].sudo().create({"name": "x"})
        logged_env.flush_all()
        assert record.create_uid.id == 2


def test_a_field_whose_comodel_is_absent_declares_no_constraint():
    class Ghost(models.Model):
        _name = "fk.ghost"
        _module = _MOD + ".ghost"
        _description = "a host whose comodel was never registered"

        name = fields.Char()
        ghost_id = fields.Many2one("fk.no.such.model")

    with model_test_env(Ghost, check_cache=False) as env:
        assert env["fk.ghost"].create({"name": "ok"}).name == "ok"


class Tag(models.Model):
    _name = "fk.tag"
    _module = _MOD
    _description = "a tag a desk can carry"
    _log_access = False

    name = fields.Char()


class TaggedDesk(models.Model):
    _inherit = "fk.desk"
    _module = _MOD

    tag_ids = fields.Many2many("fk.tag")


@pytest.fixture
def tagged_env():
    with model_test_env(Room, Desk, Tag, TaggedDesk, check_cache=False) as env:
        yield env


def test_a_link_to_a_row_that_does_not_exist_is_refused(tagged_env):
    desk = tagged_env["fk.desk"].create({"name": "d"})
    with pytest.raises(ForeignKeyViolation, match="fk_tag"):
        desk.tag_ids = [(4, 987654)]
        tagged_env.flush_all()


def test_a_link_to_a_row_that_exists_is_accepted(tagged_env):
    desk = tagged_env["fk.desk"].create({"name": "d"})
    tag = tagged_env["fk.tag"].create({"name": "t"})
    desk.tag_ids = [(4, tag.id)]
    tagged_env.flush_all()
    assert desk.tag_ids == tag
