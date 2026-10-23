# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, _, api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def _prepare_from_pos(self, order_data):
        PosSession = self.env["pos.session"]
        session = PosSession.browse(order_data["pos_session_id"])
        SaleOrderLine = self.env["sale.order.line"]
        order_lines = [
            Command.create(SaleOrderLine._prepare_from_pos(sequence, line_data[2]))
            for sequence, line_data in enumerate(order_data["lines"], start=1)
        ]
        return {
            "partner_id": order_data["partner_id"],
            "origin": _("Point of Sale %s") % (session.name),
            "client_order_ref": order_data["name"],
            "user_id": order_data["user_id"],
            "pricelist_id": order_data["pricelist_id"],
            "fiscal_position_id": order_data["fiscal_position_id"],
            "order_line": order_lines,
        }

    @api.model
    def create_order_from_pos(self, order_data, action):
        # Create Draft Sale order
        order_vals = self._prepare_from_pos(order_data)
        sale_order = self.with_context(
            pos_order_lines_data=[x[2] for x in order_data.get("lines", [])]
        ).create(order_vals)

        # Confirm Sale Order
        if action in ["confirmed", "delivered", "invoiced"]:
            sale_order.action_confirm()

        # mark picking as delivered
        if action in ["delivered", "invoiced"]:
            # Mark all moves are delivered
            for move in sale_order.mapped("picking_ids.move_ids_without_package"):
                move.quantity_done = move.product_uom_qty
            sale_order.mapped("picking_ids").button_validate()

        if action in ["invoiced"]:
            # Create and confirm invoices
            invoices = sale_order._create_invoices()
            invoices.action_post()

        return {
            "sale_order_id": sale_order.id,
        }
