# Copyright 2019-2023 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details)

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    claim_id = fields.Many2one("crm.claim", readonly=True, string="Return")

    def action_switch_invoice_into_refund_credit_note(self):
        res = super().action_switch_invoice_into_refund_credit_note()
        for move in self:
            sale_order_obj = self.env["sale.order"]
            sale_ids = sale_order_obj.search([("invoice_ids", "=", move.id)])
            return_drop_ships = (
                sale_ids.mapped("picking_ids")
                .filtered(
                    lambda x: x.picking_type_code == "incoming"
                    and x.location_dest_id.usage == "supplier"
                    and x.picking_type_id.default_location_src_id.usage == "supplier"
                    and x.picking_type_id.default_location_dest_id.usage == "customer"
                )
                .sorted(key="id")
            )
            if return_drop_ships:
                move.claim_id = return_drop_ships[-1].claim_id.id
        return res
