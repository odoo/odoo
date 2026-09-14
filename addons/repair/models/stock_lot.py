from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockLot(models.Model):
    _inherit = "stock.lot"

    repair_line_ids = fields.Many2many(
        comodel_name="repair.order",
        string="Repair Orders",
        compute="_compute_repair_line_ids",
    )
    repair_part_count = fields.Count(
        count_of="repair_line_ids",
        string="Repair part count",
    )
    in_repair_count = fields.Integer(
        string="In repair count",
        compute="_compute_in_repair_count",
    )
    repaired_count = fields.Integer(
        string="Repaired count",
        compute="_compute_repaired_count",
    )

    @api.depends("name")
    def _compute_repair_line_ids(self):
        _debug.perf.count("repair_lot_lines_compute", lots=self)
        repair_orders = defaultdict(lambda: self.env["repair.order"])
        repair_moves = self.env["stock.move"].search(
            [
                ("repair_id", "!=", False),
                ("repair_line_type", "!=", False),
                ("move_line_ids.lot_id", "in", self.ids),
                ("state", "=", "done"),
            ]
        )
        for repair_line in repair_moves:
            for rl_id in repair_line.lot_ids.ids:
                repair_orders[rl_id] |= repair_line.repair_id
        for lot in self:
            lot.repair_line_ids = repair_orders[lot.id]

    def _compute_in_repair_count(self):
        lot_data = self.env["repair.order"]._read_group(
            [("lot_id", "in", self.ids), ("state", "not in", ("done", "cancel"))],
            ["lot_id"],
            ["__count"],
        )
        result = {lot.id: count for lot, count in lot_data}
        for lot in self:
            lot.in_repair_count = result.get(lot.id, 0)

    def _compute_repaired_count(self):
        lot_data = self.env["repair.order"]._read_group(
            [("lot_id", "in", self.ids), ("state", "=", "done")],
            ["lot_id"],
            ["__count"],
        )
        result = {lot.id: count for lot, count in lot_data}
        for lot in self:
            lot.repaired_count = result.get(lot.id, 0)

    def action_lot_open_repairs(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "repair.action_repair_order_tree"
        )
        action.update(
            {
                "domain": [("lot_id", "=", self.id)],
                "context": {
                    "default_product_id": self.product_id.id,
                    "default_repair_lot_id": self.id,
                    "default_company_id": self.company_id.id or self.env.company.id,
                },
            }
        )
        return action

    def action_view_ro(self):
        self.check_singleton()

        action = {"res_model": "repair.order", "type": "ir.actions.act_window"}
        if len(self.repair_line_ids) == 1:
            action.update({"view_mode": "form", "res_id": self.repair_line_ids[0].id})
        else:
            action.update(
                {
                    "name": _("Repair orders of %s", self.name),
                    "domain": [("id", "in", self.repair_line_ids.ids)],
                    "view_mode": "list,form",
                }
            )
        return action

    def _check_lots_allowed(self, product_ids):
        _debug.logic("repair_lots_allowed_check", lots=self)
        active_repair_id = self.env.context.get("active_repair_id")
        if active_repair_id:
            active_repair = self.env["repair.order"].browse(active_repair_id)
            if active_repair and not active_repair.picking_type_id.use_create_lots:
                raise UserError(
                    _(
                        'You are not allowed to create a lot or serial number with this operation type. To change this, go on the operation type and tick the box "Create New Lots/Serial Numbers".'
                    )
                )
        return super()._check_lots_allowed(product_ids)
