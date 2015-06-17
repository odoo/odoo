# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import models, fields


##############################################
#                                            #
# Demo code: not intended for production use #
#                                            #
##############################################

class DummyProvider(models.Model):
    ''' This is a demo provider, intented to demonstrate how to implement a new shipping provider '''

    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('dummy', 'Dummy Provider')])

    def dummy_get_shipping_price_from_so(self, orders):
        res = []
        for order in orders:
            price = 10.0 * len([line for line in order.order_line if not line.is_delivery]) + 5
            res = res + [price]
        return res

    def dummy_send_shipping(self, pickings):
        res = []
        import random
        for picking in pickings:
            # For demo: random tracking number, and price can be the estimation of the SO or 1.0 more
            shipment = {'tracking_number': picking.id + random.randint(0, 123456789),
                        'exact_price': 10.0 * len(picking.move_lines) + 5 + random.randint(0, 1)}
            res = res + [shipment]
        return res

    def dummy_get_tracking_link(self, pickings):
        res = []
        for picking in pickings:
            res = res + [('https://www.odoo.com/apps/modules/online/delivery_provider?shipid=%s' % picking[0].carrier_tracking_ref)]
        return res

    def dummy_cancel_shipment(self, pickings):
        for picking in pickings:
            picking.message_post(body='Dummy Shipment cancelled')
