# Copyright 2019-2023 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details)

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    claim_id = fields.Many2one("crm.claim", readonly=True, string="Return")
    return_reason = fields.Text()

    @api.onchange("picking_type_id", "partner_id")
    def _onchange_picking_type(self):
        res = super()._onchange_picking_type()
        if (
            self.picking_type_id
            and self.claim_id.claim_type == "customer"
            and self.picking_type_code == "incoming"
        ):
            if self.partner_id:
                location_id = self.partner_id.property_stock_customer.id
            else:
                location_id, supplierloc = self.env[
                    "stock.warehouse"
                ]._get_partner_locations()
            self.location_id = location_id
        if (
            self.picking_type_id
            and self.claim_id.claim_type == "supplier"
            and self.picking_type_code == "outgoing"
        ):
            if self.partner_id:
                location_dest_id = self.partner_id.property_stock_supplier.id
            else:
                (
                    customerloc,
                    location_dest_id,
                ) = self.env["stock.warehouse"]._get_partner_locations()
            self.location_dest_id = location_dest_id
        return res

    def action_confirm(self):
        res = super().action_confirm()
        for picking in self:
            if (
                picking.claim_id
                and picking.picking_type_id.code == "incoming"
                and picking.location_id.usage == "customer"
            ):
                picking.mapped("move_ids")._action_assign()
        return res

    @api.returns("self", lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        # Note: Now we have a return location for every warehouse
        # to support multi company
        return_location = self.location_id.warehouse_id.rma_loc_id
        if self.env.context.get("return_location", False) and return_location:
            default["picking_type_id"] = return_location.warehouse_id.in_type_id.id
        return super().copy(default=default)
