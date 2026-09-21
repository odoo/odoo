"""`_add_missing_default_values(only=...)` asks for the names it will read.

`default_get` cannot be hoisted out of a batch, because a default may have a
side effect -- `stock.warehouse.orderpoint.name` draws from a sequence -- so
it runs once per record and a caller that wants defaults twice pays for the
side effects twice. `only` is how a second pass asks for less.
"""

import pytest

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_default_values_scope_dbfree"

drawn: list[int] = []


def _draw(_self):
    drawn.append(len(drawn) + 1)
    return f"SEQ{len(drawn)}"


class Doc(models.Model):
    _name = "scope.doc"
    _module = _MOD
    _description = "a document whose reference default has a side effect"
    _log_access = False

    name = fields.Char()
    kind = fields.Char(default="standard")
    reference = fields.Char(default=_draw)


@pytest.fixture
def env():
    drawn.clear()
    with model_test_env(Doc, check_cache=False) as env:
        yield env


def test_a_side_effecting_default_runs_once_per_record(env):
    env["scope.doc"].create([{"name": "a"}, {"name": "b"}, {"name": "c"}])
    assert len(drawn) == 3


def test_a_narrowed_pass_does_not_draw_a_default_it_was_not_asked_for(env):
    doc = env["scope.doc"].create({"name": "a"})
    assert len(drawn) == 1
    vals = env["scope.doc"]._add_missing_default_values({"name": "a"}, only={"kind"})
    assert vals == {"name": "a", "kind": "standard"}
    assert len(drawn) == 1, "a default outside `only` must not be evaluated"
    assert doc.reference == "SEQ1"


def test_an_unnarrowed_pass_draws_everything(env):
    env["scope.doc"]._add_missing_default_values({"name": "a"})
    assert len(drawn) == 1
    env["scope.doc"]._add_missing_default_values({"name": "b"})
    assert len(drawn) == 2


def test_only_takes_a_name_the_model_does_not_carry(env):
    vals = env["scope.doc"]._add_missing_default_values(
        {"name": "a"}, only={"kind", "no.such.field"}
    )
    assert vals == {"name": "a", "kind": "standard"}


def test_the_cache_does_not_confuse_a_narrowed_pass_with_a_wide_one(env):
    cache: dict = {}
    narrow = env["scope.doc"]._add_missing_default_values(
        {"name": "a"}, _missing_defaults_cache=cache, only={"kind"}
    )
    wide = env["scope.doc"]._add_missing_default_values(
        {"name": "a"}, _missing_defaults_cache=cache
    )
    assert set(narrow) == {"name", "kind"}
    assert set(wide) == {"name", "kind", "reference"}
