"""A delegated field answers `fields_get` from the field it delegates to.

`_description_sortable` and `_description_groupable` each have three arms: the
field is a column, the field it inherits is sortable, or the model decides.
Only the first was ever executed, so what a list view may sort by on an
`_inherits` model was pinned by nothing.
"""

import pytest

from odoo import api, fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_delegated_field_description_dbfree"


class Parent(models.Model):
    _name = "delegate.parent"
    _module = _MOD
    _description = "the model a child delegates to"
    _log_access = False

    name = fields.Char()
    tally = fields.Integer()
    shout = fields.Char(compute="_compute_shout")

    @api.depends("name")
    def _compute_shout(self):
        for parent in self:
            parent.shout = (parent.name or "").upper()


class Child(models.Model):
    _name = "delegate.child"
    _module = _MOD
    _description = "a child delegating to the parent"
    _inherits = {"delegate.parent": "parent_id"}
    _log_access = False

    parent_id = fields.Many2one(
        "delegate.parent", required=True, ondelete="cascade"
    )
    note = fields.Char()


@pytest.fixture
def env():
    with model_test_env(Parent, Child, check_cache=False) as env:
        yield env


def test_a_delegated_field_is_not_a_column_of_the_child(env):
    # the premise the rest of this file rests on: `name` reaches the child
    # through delegation, so the `is_column` arm cannot be what answers
    field = env["delegate.child"]._fields["name"]
    assert not field.is_column
    assert field.inherited_field.model_name == "delegate.parent"


@pytest.mark.parametrize("fname", ["name", "tally"])
def test_a_delegated_column_is_sortable_and_groupable(env, fname):
    description = env["delegate.child"].fields_get([fname])[fname]
    assert description["sortable"] is True
    assert description["groupable"] is True


def test_a_delegated_non_stored_compute_is_neither(env):
    # it delegates to a field that is no column either, so the third arm
    # answers and the model refuses it
    description = env["delegate.child"].fields_get(["shout"])["shout"]
    assert description["sortable"] is False
    assert description["groupable"] is False


def test_the_child_s_own_column_is_still_sortable(env):
    description = env["delegate.child"].fields_get(["note"])["note"]
    assert description["sortable"] is True
    assert description["groupable"] is True


def test_the_parent_answers_for_its_own_fields(env):
    description = env["delegate.parent"].fields_get(["name", "shout"])
    assert description["name"]["sortable"] is True
    assert description["shout"]["sortable"] is False
