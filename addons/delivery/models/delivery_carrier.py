# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import time

from openerp import api, fields, models, _
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _name = "delivery.carrier"
    _description = "Carrier"
    _order = 'sequence, id'

    name = fields.Char(string='Delivery Method', required=True, translate=True)
    sequence = fields.Integer(default=10, help="Determine the display order")
    partner_id = fields.Many2one('res.partner', string='Transport Company', required=True,
        help="The partner that is doing the delivery service.")
    product_id = fields.Many2one('product.product', string='Delivery Product', required=True)
    grid_ids = fields.One2many('delivery.grid', 'carrier_id', string='Delivery Grids', oldname='grids_id')
    available = fields.Boolean(compute="get_price", help="Is the carrier method possible with the current order.")
    price = fields.Float(compute="get_price")
    active = fields.Boolean(help="If the active field is set to False, it will allow you to hide the delivery carrier without removing it.", default=True)
    normal_price = fields.Float(help="Keep empty if the pricing depends on the advanced pricing per destination")
    free_if_more_than = fields.Boolean(string='Free If Order Total Amount Is More Than',
        default=False, help="If the order is more expensive than a certain amount, the customer can benefit from a free shipping")
    amount = fields.Float(help="Amount of the order to benefit from a free shipping, expressed in the company currency")
    use_detailed_pricelist = fields.Boolean(string='Advanced Pricing per Destination'
        , help="Check this box if you want to manage delivery prices that depends on the destination, the weight, the total of the order, etc.""")
    pricelist_ids = fields.One2many('delivery.grid', 'carrier_id', string='Advanced Pricing')

    @api.multi
    def name_get(self):
        order_id = self.env.context.get('order_id')
        if order_id:
            currency = self.env['sale.order'].browse(order_id).pricelist_id.currency_id.name or ''
            return [(rec.id, '%s (%s %s)' % (rec.name, rec.price, currency)) for rec in self]
        return super(DeliveryCarrier, self).name_get()

    @api.multi
    def get_price(self):
        SaleOrder = self.env['sale.order']
        for carrier in self:
            order_id = self.env.context.get('order_id')
            price = available = False
            if order_id:
                order = SaleOrder.browse(order_id)
                carrier_grid = carrier.grid_get(order.partner_shipping_id)
                if carrier_grid:
                    try:
                        price = carrier.grid_ids.get_price(order, time.strftime('%Y-%m-%d'))
                        available = True
                    except UserError, e:
                        # no suitable delivery method found, probably
                        # configuration error
                        _logger.info("Carrier %s: %s", carrier.name, e.name)
                        price = 0.0
                else:
                    price = 0.0
                carrier.price = price
                carrier.available = available

    @api.one
    def grid_get(self, contact_id):
        contact = self.env['res.partner'].browse(contact_id)
        for carrier in self:
            for grid in carrier.grid_ids:
                get_id = lambda x: x.id
                country_ids = map(get_id, grid.country_ids)
                state_ids = map(get_id, grid.state_ids)
                if country_ids and not contact.country_id.id in country_ids:
                    continue
                if state_ids and not contact.state_id.id in state_ids:
                    continue
                if grid.zip_from and (contact.zip or '') < grid.zip_from:
                    continue
                if grid.zip_to and (contact.zip or '') > grid.zip_to:
                    continue
                return grid.id
        return False

    @api.multi
    def create_grid_lines(self, vals):
        GridLine = self.env['delivery.grid.line']
        Grid = self.env['delivery.grid']
        for record in self:
            # if using advanced pricing per destination: do not change
            if record.use_detailed_pricelist:
                continue
            # not using advanced pricing per destination: override grid
            grids = Grid.search([('carrier_id', '=', record.id)])
            if grids and not (record.normal_price or record.free_if_more_than):
                grids.unlink()
                grids = None

            # Check that float, else 0.0 is False
            if not (isinstance(record.normal_price, float) or record.free_if_more_than):
                continue

            if not grids:
                grid_data = {
                    'name': record.name,
                    'carrier_id': record.id,
                    'sequence': 10,
                }
                grids = Grid.create(grid_data)
                grids.line_ids.unlink()

            # create the grid lines
            if record.free_if_more_than:
                line_data = {
                    'grid_id': grids.id,
                    'name': _('Free if more than %.2f') % record.amount,
                    'variable': 'price',
                    'operator': '>=',
                    'max_value': record.amount,
                    'standard_price': 0.0,
                    'list_price': 0.0,
                }
                GridLine.create(line_data)

            if isinstance(record.normal_price, float):
                line_data = {
                    'grid_id': grids.id,
                    'name': _('Default price'),
                    'variable': 'price',
                    'operator': '>=',
                    'max_value': 0.0,
                    'standard_price': record.normal_price,
                    'list_price': record.normal_price,
                }
                GridLine.create(line_data)
        return True

    @api.multi
    def write(self, vals):
        res = super(DeliveryCarrier, self).write(vals)
        self.create_grid_lines(vals)
        return res

    @api.model
    def create(self, vals):
        carrier = super(DeliveryCarrier, self).create(vals)
        carrier.create_grid_lines(vals)
        return carrier
