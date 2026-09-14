from unittest import mock

from odoo import api, fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_recompute_missing"


class Order(models.Model):
    _name = "rm.order"
    _module = _MOD
    _description = "order"
    _log_access = False

    name = fields.Char()
    line_ids = fields.One2many("rm.line", "order_id")


class Line(models.Model):
    _name = "rm.line"
    _module = _MOD
    _description = "line"
    _log_access = False

    order_id = fields.Many2one("rm.order", ondelete="cascade", required=True)
    label = fields.Char(compute="_compute_label", store=True)
    upper = fields.Char(compute="_compute_upper", store=True)
    length = fields.Integer(compute="_compute_length", store=True)

    @api.depends("order_id.name")
    def _compute_label(self):
        for line in self:
            line.label = line.order_id["name"]

    @api.depends("order_id.name")
    def _compute_upper(self):
        for line in self:
            line.upper = (line.order_id["name"] or "").upper()

    @api.depends("order_id.name")
    def _compute_length(self):
        for line in self:
            line.length = len(line.order_id["name"] or "")


def test_records_deleted_by_cascade_are_dropped_from_every_pending_field():
    with model_test_env(Order, Line) as env:
        orders = env["rm.order"].create(
            [{"name": f"o{i}", "line_ids": [(0, 0, {}), (0, 0, {})]} for i in range(3)]
        )
        env.flush_all()
        lines = orders.line_ids
        assert lines and all(line.label for line in lines)
        backend = env.backend
        with mock.patch.object(
            type(backend), "get_existing_ids", wraps=backend.get_existing_ids
        ) as existing:
            orders.unlink()
            env.flush_all()
        # one existence check inside the first field's read, one in its
        # recompute; the two other pending fields never ask again
        assert existing.call_count == 2
        assert not lines.exists()
        assert not env.fields_to_compute()
