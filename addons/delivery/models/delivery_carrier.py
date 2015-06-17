# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import time

from openerp import models, fields, api, _

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'
    _description = "Carrier"

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

    name = fields.Char('Delivery Method', required=True)
    partner_id = fields.Many2one('res.partner', 'Transport Company', required=True, help="The partner that is doing the delivery service.")
    product_id = fields.Many2one('product.product', 'Delivery Product', required=True)
    active = fields.Boolean('Active', default=True, help="If the active field is set to False, it will allow you to hide the delivery carrier without removing it.")

    # TODO move in delivery_grid
    grids_id = fields.One2many('delivery.grid', 'carrier_id', 'Delivery Grids')
    normal_price = fields.Float('Normal Price', help="Keep empty if the pricing depends on the advanced pricing per destination")
    free_if_more_than = fields.Boolean('Free If Order Total Amount Is More Than', help="If the order is more expensive than a certain amount, the customer can benefit from a free shipping")
    amount = fields.Float('Amount', help="Amount of the order to benefit from a free shipping, expressed in the company currency")
    use_detailed_pricelist = fields.Boolean('Advanced Pricing per Destination', help="Check this box if you want to manage delivery prices that depends on the destination, the weight, the total of the order, etc.")
    pricelist_ids = fields.One2many('delivery.grid', 'carrier_id', 'Advanced Pricing')

    @api.multi
    def write(self, vals):
        res = super(DeliveryCarrier, self).write(vals)
        self.create_grid_lines(vals)
        return res

    @api.model
    def create(self, vals):
        res = super(DeliveryCarrier, self).create(vals)
        res.create_grid_lines(vals)
        return res

    def compute_delivery_price(self, orders):
        self.ensure_one()
        res = []

        if self.delivery_type != 'grid':
            res = self.get_shipping_price_from_so(orders)
        else:
            # TODO move into delivery_grid
            # this is the get_shipping_price_from_so of delivery_grid
            for order in orders:
                price = 0.0
                carrier_grid = self.grid_get(order.partner_shipping_id)
                if carrier_grid:
                    price = carrier_grid.get_price(order, time.strftime('%Y-%m-%d'))
                    res = res + price
        return res

    @api.multi
    def grid_get(self, contact):
        contact.ensure_one()
        # TODO move into delivery_grid
        for carrier in self:
            for grid in carrier.grids_id:
                country_ids = grid.country_ids.ids
                state_ids = grid.state_ids.ids
                if country_ids and contact.country_id.id not in country_ids:
                    continue
                if state_ids and contact.state_id.id not in state_ids:
                    continue
                if grid.zip_from and (contact.zip or '') < grid.zip_from:
                    continue
                if grid.zip_to and (contact.zip or '') > grid.zip_to:
                    continue
                return grid

        return False

    #########################################
    # Hooks to implement external providers #
    #########################################

    # TODO define and handle exceptions that could be thrown by providers

    delivery_type = fields.Selection([('grid', 'Delivery Method with grid')], string="Delivery Type", default='grid', required='True')

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
        :return list: A list of dictionaries (one per picking) containing the exact_price of the shipping
                      and its tracking_number
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
