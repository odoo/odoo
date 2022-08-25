# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _, api
from odoo.exceptions import ValidationError


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    # Onsite delivery means the client comes to a physical store to get the products himself.
    delivery_type = fields.Selection(selection_add=[
        ('onsite', 'Pickup in store')
    ], ondelete={'onsite': 'set default'})

    # If set, the sales order shipping address will take this warehouse's address.
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')

    @api.constrains('warehouse_id', 'company_id')
    def _check_warehouse_company(self):
        for carrier in self:
            if carrier.warehouse_id.company_id and carrier.company_id != carrier.warehouse_id.company_id:
                raise ValidationError(_("The picking site and warehouse must share the same company"))

    def onsite_rate_shipment(self, order):
        """
        Required to show the price on the checkout page for the onsite delivery type
        """
        return {
            'success': True,
            'price': self.product_id.list_price,
            'error_message': False,
            'warning_message': False
        }

    def onsite_send_shipping(self, pickings):
        return [{
            'exact_price': p.carrier_id.fixed_price,
            'tracking_number': False
        } for p in pickings]

    def onsite_cancel_shipment(self, pickings):
        pass  # No need to communicate to an external service, however the method must exist so that cancel_shipment() works.
