# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Business Applications
#    Copyright (c) 2015 Odoo S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
from openerp import models, fields, api
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'
    ''' A Shipping Provider

    In order to add your own external provider, follow these steps:

    1. Create your model MyProvider that _inherit 'delivery.carrier'
    2. Extend the selection of the field "delivery_type" with a pair
       ('<my_provider>', 'My Provider')
    3. Add your methods:
       <my_provider>_get_shipping_price_from_so
       <my_provider>_send_shipping
       <my_provider>_open_tracking_page
       <my_provider>_cancel_shipment
       (they are documented hereunder)
    '''

    # -------------------------------- #
    # Internals for shipping providers #
    # -------------------------------- #

    delivery_type = fields.Selection([('grid', 'Default Delivery')], string="Delivery Type", default='grid', required='True')

    price = fields.Float(compute='get_price')
    available = fields.Boolean(compute='get_price')

    @api.one
    def get_price(self):
        SaleOrder = self.env['sale.order']

        self.available = False
        self.price = False

        order_id = self.env.context.get('order_id')
        if order_id:
            # FIXME: temporary hack until we refactor the delivery API in master

            if self.delivery_type != 'grid':
                try:
                    order = SaleOrder.browse(order_id)
                    self.price = self.get_shipping_price_from_so(order)[0]
                    self.available = True
                except UserError as e:
                        # no suitable delivery method found, probably configuration error
                        _logger.info("Carrier %s: %s, not found", self.name, e.name)
                        self.price = 0.0
            else:
                res = super(DeliveryCarrier, self).get_price('price', [])
                self.available = res[self.id]['available']
                self.price = res[self.id]['price']

    # -------------------------- #
    # API for external providers #
    # -------------------------- #

    # TODO define and handle exceptions that could be thrown by providers

    def get_shipping_price_from_so(self, orders):
        ''' For every sale order, compute the price of the shipment

        :param orders: A recordset of sale orders
        :return list: A list of floats, containing the estimated price for the shipping of the sale order
        '''
        self.ensure_one()
        if hasattr(self, '%s_get_shipping_price_from_so' % self.delivery_type):
            return getattr(self, '%s_get_shipping_price_from_so' % self.delivery_type)(orders)

    def send_shipping(self, pickings):
        ''' Send the package to the service provider

        :param pickings: A recordset of pickings
        :return list: A list of dictionaries (one per picking) containing of the form::
                         { 'exact_price': price,
                           'tracking_number': number }
        '''
        self.ensure_one()
        if hasattr(self, '%s_send_shipping' % self.delivery_type):
            return getattr(self, '%s_send_shipping' % self.delivery_type)(pickings)

    def get_tracking_link(self, pickings):
        ''' Ask the tracking link to the service provider

        :param pickings: A recordset of pickings
        :return list: A list of string URLs, containing the tracking links for every picking
        '''
        self.ensure_one()
        if hasattr(self, '%s_get_tracking_link' % self.delivery_type):
            return getattr(self, '%s_get_tracking_link' % self.delivery_type)(pickings)

    def cancel_shipment(self, pickings):
        ''' Cancel a shipment

        :param pickings: A recordset of pickings
        '''
        self.ensure_one()
        if hasattr(self, '%s_cancel_shipment' % self.delivery_type):
            return getattr(self, '%s_cancel_shipment' % self.delivery_type)(pickings)
