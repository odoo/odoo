from collections import defaultdict

from odoo import Command, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockLot(models.Model):
    _inherit = "stock.lot"

    sale_order_ids = fields.Many2many(
        comodel_name="sale.order",
        string="Sales Orders",
        compute="_compute_sale_orders",
    )
    sale_order_count = fields.Integer(
        string="Sale order count",
        compute="_compute_sale_orders",
    )

    @api.depends("quant_ids")
    def _compute_sale_orders(self):
        sale_orders = defaultdict(set)
        move_lines = self.env["stock.move.line"].search(
            [
                ("lot_id", "in", self.ids),
                ("state", "=", "done"),
                ("move_id.sale_line_id.order_id", "!=", False),
                (
                    "move_id.picking_id.location_dest_id.usage",
                    "in",
                    ("customer", "transit"),
                ),
            ]
        )
        orders = move_lines.move_id.sale_line_id.order_id
        readable_order_ids = set(
            orders.with_user(self.env.user)._filtered_access("read").ids
        )
        for ml in move_lines:
            so = ml.move_id.sale_line_id.order_id
            if so.id in readable_order_ids:
                sale_orders[ml.lot_id.id].add(so.id)
        _debug.perf.count(
            "lot_sale_orders",
            lots=len(self),
            move_lines=len(move_lines),
            readable_orders=len(readable_order_ids),
            all_orders=len(orders),
        )
        for lot in self:
            so_ids = sale_orders.get(lot.id, set())
            lot.sale_order_ids = [Command.set(list(so_ids))]
            lot.sale_order_count = len(so_ids)

    def action_view_so(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "sale.action_sale_order",
        )
        action["domain"] = [("id", "in", self.mapped("sale_order_ids.id"))]
        action["context"] = dict(self.env.context, create=False)
        return action
