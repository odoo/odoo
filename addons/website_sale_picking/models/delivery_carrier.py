# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    # Onsite delivery means the client comes to a physical store to get the products himself.
    delivery_type = fields.Selection(selection_add=[
        ('onsite', 'Pickup in store')
    ], ondelete={'onsite': 'set default'})

    # If set, the sales order shipping address will take this warehouse's address.
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', check_company=True)

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
