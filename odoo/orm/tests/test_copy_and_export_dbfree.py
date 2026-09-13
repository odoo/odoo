import pytest

from odoo import api, fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_copy_and_export_dbfree"


class Tag(models.Model):
    _name = "cp.tag"
    _module = _MOD
    _description = "tag"
    _log_access = False

    name = fields.Char()


class Line(models.Model):
    _name = "cp.line"
    _module = _MOD
    _description = "line"
    _log_access = False

    order_id = fields.Many2one("cp.order", ondelete="cascade")
    name = fields.Char()
    serial = fields.Char(copy=False)


class Order(models.Model):
    _name = "cp.order"
    _module = _MOD
    _description = "order"
    _log_access = False

    name = fields.Char()
    ref = fields.Char(copy=False)
    tag_ids = fields.Many2many("cp.tag")
    line_ids = fields.One2many("cp.line", "order_id", copy=True)
    note_ids = fields.One2many("cp.line", "order_id", domain=[("name", "=", "n")])
    total = fields.Integer(compute="_compute_total", store=True)

    @api.depends("line_ids")
    def _compute_total(self):
        for order in self:
            order.total = len(order.line_ids)


@pytest.fixture
def env():
    with model_test_env(Tag, Line, Order) as env:
        yield env


def _order(env):
    tags = env["cp.tag"].create([{"name": "a"}, {"name": "b"}])
    return env["cp.order"].create(
        {
            "name": "o",
            "ref": "REF",
            "tag_ids": [(6, 0, tags.ids)],
            "line_ids": [
                (0, 0, {"name": "l1", "serial": "S1"}),
                (0, 0, {"name": "l2", "serial": "S2"}),
            ],
        }
    )


def test_copy_duplicates_lines_links_tags_and_skips_copy_false(env):
    order = _order(env)
    assert not Order.note_ids.copy, "a one2many is not copied unless it says so"
    copy = order.copy()
    assert copy.name == "o"
    assert not copy.ref
    assert copy.tag_ids == order.tag_ids
    assert copy.line_ids.mapped("name") == ["l1", "l2"]
    assert not any(copy.line_ids.mapped("serial"))
    assert copy.line_ids.mapped("order_id") == copy
    assert copy.total == 2
    assert order.line_ids.mapped("serial") == ["S1", "S2"]


def test_copy_default_overrides_and_blocks_a_field(env):
    order = _order(env)
    copy = order.copy({"name": "renamed", "line_ids": []})
    assert copy.name == "renamed"
    assert not copy.line_ids
    assert copy.total == 0


def test_copy_data_refuses_a_recordset_with_a_duplicate(env):
    order = _order(env)
    with pytest.raises(ValueError, match="more than once"):
        (order + order).copy_data()


def test_copy_of_several_records_answers_one_copy_each(env):
    first, second = _order(env), _order(env)
    copies = (first + second).copy()
    assert len(copies) == 2
    assert copies.mapped("line_ids").mapped("order_id") == copies
    assert all(len(c.line_ids) == 2 for c in copies)


def test_export_data_walks_lines_and_tags(env):
    order = _order(env)
    result = order.export_data(
        ["name", "tag_ids/name", "line_ids/name", "line_ids/serial"]
    )
    assert result["datas"] == [
        ["o", "a,b", "l1", "S1"],
        ["", "", "l2", "S2"],
    ]
