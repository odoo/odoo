from collections import defaultdict

from odoo import api, fields, models


class StockLot(models.Model):
    _inherit = "stock.lot"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    purchase_order_ids = fields.Many2many(
        comodel_name="purchase.order",
        string="Purchase Orders",
        compute="_compute_purchase_order_ids",
    )
    purchase_order_count = fields.Integer(
        string="Purchase order count",
        compute="_compute_purchase_order_ids",
    )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    @api.depends("name")
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
            lot.purchase_order_count = len(lot.purchase_order_ids)

    # ------------------------------------------------------------
    # ACTION METHODS
    # ------------------------------------------------------------

    def action_view_po(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase.purchase_form_action",
        )
        action["domain"] = [("id", "in", self.mapped("purchase_order_ids.id"))]
        action["context"] = dict(self.env.context, create=False)
        return action
