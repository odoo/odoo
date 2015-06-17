# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import models, fields

class GridCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('grid', 'Delivery Method with grid')])

    # def grid_get_shipping_price_from_so(self, orders):
    #     res = []
    #     for order in orders:
    #         price = 10.0 * len([line for line in order.order_line if not line.is_delivery]) + 5
    #         res = res + [price]
    #     return res

    # def grid_send_shipping(self, pickings):
    #     res = []
    #     import random
    #     for picking in pickings:
    #         # For demo: random tracking number, and price can be the estimation of the SO or 1.0 more
    #         shipment = {'tracking_number': picking.id + random.randint(0, 123456789),
    #                     'exact_price': 10.0 * len(picking.move_lines) + 5 + random.randint(0, 1)}
    #         res = res + [shipment]
    #     return res

    # def grid_get_tracking_link(self, pickings):
    #     return []

    # def grid_cancel_shipment(self, pickings):
    #     pass
