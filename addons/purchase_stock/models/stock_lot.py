from collections import defaultdict

from odoo import api, fields, models


class StockLot(models.Model):
    _inherit = "stock.lot"

    purchase_order_ids = fields.Many2many(
        comodel_name="purchase.order",
        string="Purchase Orders",
        compute="_compute_purchase_order_ids",
    )
    purchase_order_count = fields.Count(
        count_of="purchase_order_ids",
        string="Purchase order count",
    )

    @api.depends("quant_ids")
    def _compute_purchase_order_ids(self):
        purchase_orders = defaultdict(lambda: self.env["purchase.order"])
        for move_line in self.env["stock.move.line"].search(
            [("lot_id", "in", self.ids), ("state", "=", "done")],
        ):
            move = move_line.move_id
            if (
                move.picking_id.location_id.usage in ("supplier", "transit")
                and move.purchase_line_id.order_id
            ):
                purchase_orders[move_line.lot_id.id] |= move.purchase_line_id.order_id
        for lot in self:
            lot.purchase_order_ids = purchase_orders[lot.id]

    def action_view_po(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "purchase.action_purchase_order_2",
        )
        action["domain"] = [("id", "in", self.purchase_order_ids.ids)]
        action["context"] = dict(self.env.context, create=False)
        return action
