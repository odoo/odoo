# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    shipper_order_id = fields.Char("Shipper Order ID", copy=False)
    shipper_order_amount = fields.Integer("Shipper Order Amount", copy=False)

    def shipper_create_order(self):
        self.ensure_one()
        res = self.carrier_id.shipper_create_order(self)
        if self.shipper_order_id is None:
            raise UserError(_("Something went wrong when creating Shipper order. Please try again"))
        return res

    def shipper_cancel_order(self):
        self.ensure_one()
        res = self.carrier_id.shipper_cancel_shipment(self)
        if self.shipper_order_id is None:
            raise UserError(_("Something went wrong when cancelling Shipper order. Please try again"))
        return res
