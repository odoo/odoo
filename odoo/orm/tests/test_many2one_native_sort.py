"""A many2one sorts through the cache scan, but only when the comodel is
ordered by id -- because SQL sorts a many2one through the comodel's own
`_order`, and only then do the two agree.

Before `Many2one.cache_is_orderable`, `can_scan_sorted` refused every
many2one and the `is_many2one` guard in `_sorted_by_ids` was unreachable.
"""

import pytest

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env
from odoo.orm.models.mixins._cache_scan import can_scan_sorted

_MOD = "test_many2one_native_sort"


class ById(models.Model):
    _name = "m2s.by_id"
    _module = _MOD
    _description = "comodel ordered by id"
    _log_access = False

    name = fields.Char()


class ByName(models.Model):
    _name = "m2s.by_name"
    _module = _MOD
    _description = "comodel ordered by name"
    _order = "name, id"
    _log_access = False

    name = fields.Char()


class Holder(models.Model):
    _name = "m2s.holder"
    _module = _MOD
    _description = "holder"
    _log_access = False

    name = fields.Char()
    by_id = fields.Many2one("m2s.by_id")
    by_name = fields.Many2one("m2s.by_name")


def _populate(env):
    ids = env["m2s.by_id"].create([{"name": n} for n in "cab"])
    names = env["m2s.by_name"].create([{"name": n} for n in "cab"])
    holders = env["m2s.holder"].create(
        [
            {"name": f"h{i}", "by_id": ids[i % 3].id, "by_name": names[i % 3].id}
            for i in range(9)
        ]
        + [{"name": "h9"}]  # one with both unset, so NULLs take part
    )
    env.flush_all()
    holders.mapped("by_id")
    holders.mapped("by_name")
    return holders


def test_a_many2one_declares_its_cache_orderable():
    with model_test_env(ById, ByName, Holder) as env:
        assert can_scan_sorted(env["m2s.holder"]._fields["by_id"])


@pytest.mark.parametrize(
    "order",
    [
        "by_id, id",
        "by_id desc, id",
        "by_id nulls last, id",
        "by_id desc nulls last, id",
        "by_id, name desc",
    ],
)
def test_the_native_scan_sorts_as_the_python_fallback_does(order):
    field = Holder.by_id.__class__
    with model_test_env(ById, ByName, Holder) as env:
        holders = _populate(env)
        field.cache_is_orderable = False
        try:
            expected = holders.sorted(order).ids
        finally:
            field.cache_is_orderable = True
        assert holders.sorted(order).ids == expected


def test_a_comodel_not_ordered_by_id_still_takes_the_python_path():
    # the guard this flag made reachable: the two paths disagree there,
    # because SQL would sort through the comodel's own order
    with model_test_env(ById, ByName, Holder) as env:
        holders = _populate(env)
        assert holders._sorted_by_ids("by_name, id", False) is None
        assert holders._sorted_by_ids("by_id, id", False) is not None


def test_new_records_sort_beside_real_ones():
    field = Holder.by_id.__class__
    with model_test_env(ById, ByName, Holder) as env:
        holders = _populate(env)
        comodel = env["m2s.by_id"].search([], limit=1)
        fresh = env["m2s.holder"].new({"name": "new", "by_id": comodel.id})
        mixed = holders | fresh
        mixed.mapped("by_id")
        field.cache_is_orderable = False
        try:
            expected = mixed.sorted("by_id, id").ids
        finally:
            field.cache_is_orderable = True
        assert mixed.sorted("by_id, id").ids == expected
