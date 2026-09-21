"""The tier refuses a search PostgreSQL refuses, by asking its compiler.

A hand-written rule for "which fields can SQL search and order by" was wrong
in four ways at once, so what stands here instead is the compiler itself:
the same two calls `_prepare_postgres_search_query` makes, with the SQL
discarded. These tests pin the cases the hand-written rule got wrong.
"""

import pytest

from odoo import api, fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_search_compilation_dbfree"


class Group(models.Model):
    _name = "compile.group"
    _module = _MOD
    _description = "a group with a stored rank and an unstored shout"
    _log_access = False

    rank = fields.Integer()
    shout = fields.Char(compute="_compute_shout")

    @api.depends("rank")
    def _compute_shout(self):
        for group in self:
            group.shout = f"R{group.rank}"


class Item(models.Model):
    _name = "compile.item"
    _module = _MOD
    _description = "an item pointing at a group"
    _log_access = False

    code = fields.Char()
    group_id = fields.Many2one("compile.group")
    group_rank = fields.Integer(related="group_id.rank")


@pytest.fixture
def env():
    with model_test_env(Group, Item, check_cache=False) as env:
        group = env["compile.group"].create({"rank": 7})
        env["compile.item"].create({"code": "a", "group_id": group.id})
        env.flush_all()
        yield env


def test_a_condition_on_a_non_stored_compute_is_refused(env):
    with pytest.raises(ValueError, match=r"compile\.group\.shout"):
        env["compile.group"].search([("shout", "=", "R7")])


def test_a_later_segment_of_a_dotted_path_is_reached(env):
    # the rule this replaces read only the first segment, and `group_id` is
    # stored, so the condition passed unexamined
    with pytest.raises(ValueError, match=r"compile\.group\.shout"):
        env["compile.item"].search([("group_id.shout", "=", "R7")])


def test_an_any_sub_domain_is_reached(env):
    # `iter_conditions()` yields the `group_id` condition and never descends,
    # so the rule this replaces never saw `shout` at all
    with pytest.raises(ValueError, match=r"compile\.group\.shout"):
        env["compile.item"].search([("group_id", "any", [("shout", "=", "R7")])])


def test_a_condition_on_a_stored_field_is_allowed(env):
    assert env["compile.item"].search([("group_id.rank", "=", 7)])
    assert env["compile.group"].search([("rank", "=", 7)])


def test_a_condition_on_a_non_stored_related_is_allowed(env):
    # it compiles to a join, so the compiler takes it and so must this
    assert env["compile.item"].search([("group_rank", "=", 7)])


def test_a_custom_domain_with_a_python_predicate_is_never_compiled(env):
    def sql_only(model, alias, query):
        raise AssertionError("the Python adapter must not compile custom SQL")

    items = env["compile.item"].search([])
    domain = fields.Domain.custom(
        to_sql=sql_only, predicate=lambda record: record["code"] == "a"
    ) & fields.Domain("id", "in", items.ids)

    assert env["compile.item"].search(domain) == items
