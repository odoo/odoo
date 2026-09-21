"""The DB-free tier evaluates a domain through `filtered_domain`, in Python,
so it could answer a condition on a non-stored computed field. PostgreSQL
cannot: `_field_to_sql` refuses with "Cannot convert ... to SQL because it is
not stored". Measured on a live database against `ir.model.modules`,
`ir.model.count` and `ir.model.fields.selection`, all three raise exactly that.

A search this tier answers and the database refuses is a test that passes here
and fails there, so the twin refuses it too.
"""

import pytest

from odoo import api, fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_memory_refuses_unsearchable"


class Target(models.Model):
    _name = "mru.target"
    _module = _MOD
    _description = "target"
    _log_access = False

    name = fields.Char()


class Holder(models.Model):
    _name = "mru.holder"
    _module = _MOD
    _description = "holder"
    _log_access = False

    code = fields.Char()
    stored_id = fields.Many2one("mru.target")
    live_id = fields.Many2one("mru.target", compute="_compute_links")
    related_id = fields.Many2one("mru.target", related="stored_id")
    searchable_id = fields.Many2one(
        "mru.target", compute="_compute_links", search="_search_searchable_id"
    )

    @api.depends("stored_id")
    def _compute_links(self):
        for record in self:
            record.live_id = record.stored_id
            record.searchable_id = record.stored_id

    def _search_searchable_id(self, operator, value):
        return [("stored_id", operator, value)]


def _seeded(env):
    target = env["mru.target"].create({"name": "t"})
    env["mru.holder"].create({"code": "h", "stored_id": target.id})
    env.flush_all()
    return target


def test_a_non_stored_field_with_no_search_is_refused():
    with model_test_env(Target, Holder) as env:
        target = _seeded(env)
        with pytest.raises(ValueError, match="not stored"):
            env["mru.holder"].search([("live_id", "=", target.id)])


def test_the_message_is_the_one_postgresql_gives():
    with model_test_env(Target, Holder) as env:
        target = _seeded(env)
        with pytest.raises(ValueError) as caught:
            env["mru.holder"].search([("live_id", "=", target.id)])
        assert "Cannot convert mru.holder.live_id to SQL" in str(caught.value)


@pytest.mark.parametrize("fname", ["stored_id", "related_id", "searchable_id"])
def test_a_field_the_database_can_search_is_still_searched(fname):
    with model_test_env(Target, Holder) as env:
        target = _seeded(env)
        found = env["mru.holder"].search([(fname, "=", target.id)])
        assert len(found) == 1


def test_a_plain_stored_condition_beside_a_refused_one_still_refuses():
    with model_test_env(Target, Holder) as env:
        target = _seeded(env)
        with pytest.raises(ValueError, match="not stored"):
            env["mru.holder"].search([("code", "=", "h"), ("live_id", "=", target.id)])
