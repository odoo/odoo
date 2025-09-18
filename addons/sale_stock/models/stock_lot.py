from collections import defaultdict

from odoo import Command, api, fields, models


class StockLot(models.Model):
    _inherit = "stock.lot"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    sale_order_ids = fields.Many2many(
        comodel_name="sale.order",
        string="Sales Orders",
        compute="_compute_sale_order_ids",
    )
    sale_order_count = fields.Integer(
        string="Sale order count",
        compute="_compute_sale_order_ids",
    )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    @api.depends("name")
    def _compute_sale_order_ids(self):
        sale_orders = defaultdict(set)
        move_lines = self.env["stock.move.line"].search([
            ("lot_id", "in", self.ids),
            ("state", "=", "done"),
            ("move_id.sale_line_id.order_id", "!=", False),
            ("move_id.picking_id.location_dest_id.usage", "in", ("customer", "transit")),
        ])
        for ml in move_lines:
            so = ml.move_id.sale_line_id.order_id
            if so.with_user(self.env.user).has_access("read"):
                sale_orders[ml.lot_id.id].add(so.id)
        for lot in self:
            so_ids = sale_orders.get(lot.id, set())
            lot.sale_order_ids = [Command.set(list(so_ids))]
            lot.sale_order_count = len(so_ids)

    # ------------------------------------------------------------
    # ACTION METHODS
    # ------------------------------------------------------------

    def action_view_so(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "sale.action_sale_order",
        )
        action["domain"] = [("id", "in", self.mapped("sale_order_ids.id"))]
        action["context"] = dict(self.env.context, create=False)
        return action
