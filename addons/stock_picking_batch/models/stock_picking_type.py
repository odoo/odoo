from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    count_picking_batch = fields.Integer(compute="_compute_picking_count")
    count_picking_wave = fields.Integer(compute="_compute_picking_count")

    def _compute_picking_count(self):
        super()._compute_picking_count()
        data = self.env["stock.picking.batch"]._read_group(
            [
                ("state", "not in", ("done", "cancel")),
                ("picking_type_id", "in", self.ids),
            ],
            ["picking_type_id", "is_wave"],
            ["__count"],
        )
        count = {
            (picking_type.id, is_wave): count for picking_type, is_wave, count in data
        }
        for record in self:
            record.count_picking_wave = count.get((record.id, True), 0)
            record.count_picking_batch = count.get((record.id, False), 0)

    def action_batch(self):
        _debug.pipeline("picking_batch_action", picking_types=self)
        action = self._prepare_action_by_xml_id(
            "stock_picking_batch.stock_picking_batch_action"
        )
        if self.env.context.get("view_mode"):
            del action["mobile_view_mode"]
            del action["views"]
            action["view_mode"] = self.env.context["view_mode"]
        return action

    def action_wave(self):
        _debug.pipeline("picking_wave_action", picking_types=self)
        return self._prepare_action_by_xml_id(
            "stock_picking_batch.action_picking_tree_wave"
        )

    def _is_auto_batch_grouped(self):
        _debug.logic("auto_batch_grouped_check", picking_types=self)
        self.check_singleton()
        return self.auto_batch and any(
            self[key] for key in self._get_batch_group_by_keys()
        )

    def _is_auto_wave_grouped(self):
        _debug.logic("auto_wave_grouped_check", picking_types=self)
        self.check_singleton()
        return self.auto_batch and any(
            self[key] for key in self._get_wave_group_by_keys()
        )
