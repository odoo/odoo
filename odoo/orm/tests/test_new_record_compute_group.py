"""A value written to a new record must survive its own compute group.

A stored computed field on a `new()` record is lazy: neither cached nor
scheduled. So a write to one field of a group, followed by a read of another,
used to run the group's compute -- which assigns every field of the group --
straight over the value just written. That is the onchange path: a form writes
one field and reads another.
"""

import pytest

from odoo import api, fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_new_record_compute_group"


class Pair(models.Model):
    _name = "ncg.pair"
    _module = _MOD
    _description = "pair"
    _log_access = False

    base = fields.Integer()
    left = fields.Integer(compute="_compute_pair", store=True, readonly=False)
    right = fields.Integer(compute="_compute_pair", store=True, readonly=False)

    @api.depends("base")
    def _compute_pair(self):
        for record in self:
            record.left = record.base
            record.right = record.base * 10


def _written(env, record, how):
    if how == "write":
        record.write({"left": 5})
    else:
        record.left = 5
    sibling = record.right
    return record.left, sibling


@pytest.mark.parametrize("how", ["write", "assignment"])
def test_a_new_record_keeps_what_was_written_to_it(how):
    with model_test_env(Pair) as env:
        record = env["ncg.pair"].new({"base": 1})
        left, right = _written(env, record, how)
        assert right == 10, "the sibling still computes"
        assert left == 5, "the group's compute must not run over the write"


@pytest.mark.parametrize("how", ["write", "assignment"])
def test_a_real_record_with_a_cold_sibling_behaves_the_same(how):
    with model_test_env(Pair) as env:
        record = env["ncg.pair"].create({"base": 1})
        env.flush_all()
        env.invalidate_all()
        left, right = _written(env, record, how)
        assert right == 10
        assert left == 5


def test_the_sibling_is_settled_before_the_write_not_after():
    # the group must be materialised while nothing is protected, so that the
    # later read is a cache hit rather than a compute
    with model_test_env(Pair) as env:
        right_field = env["ncg.pair"]._fields["right"]
        record = env["ncg.pair"].new({"base": 1})
        assert env.core.get_field_data(right_field).get(record.id, "?") == "?"
        record.write({"left": 5})
        assert env.core.get_field_data(right_field).get(record.id) == 10


def test_writing_the_whole_group_keeps_both_values():
    with model_test_env(Pair) as env:
        record = env["ncg.pair"].new({"base": 1})
        record.write({"left": 5, "right": 7})
        assert (record.left, record.right) == (5, 7)


def test_a_dependency_change_still_recomputes_the_group():
    # the write must not freeze the group: changing `base` recomputes both
    with model_test_env(Pair) as env:
        record = env["ncg.pair"].new({"base": 1})
        record.write({"left": 5})
        assert record.left == 5
        record.base = 3
        assert (record.left, record.right) == (3, 30)
