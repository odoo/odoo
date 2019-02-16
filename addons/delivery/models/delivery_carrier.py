# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError
from openerp.tools.safe_eval import safe_eval as eval

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _name = 'delivery.carrier'
    _inherits = {'product.product': 'product_id'}
    _description = "Carrier"
    _order = 'sequence, id'

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

    sequence = fields.Integer(help="Determine the display order", default=10)
    # This field will be overwritten by internal shipping providers by adding their own type (ex: 'fedex')
    delivery_type = fields.Selection([('fixed', 'Fixed Price'), ('base_on_rule', 'Based on Rules')], string='Price Computation', default='fixed', required=True)
    product_type = fields.Selection(related='product_id.type', default='service')
    product_sale_ok = fields.Boolean(related='product_id.sale_ok', default=False)
    partner_id = fields.Many2one('res.partner', string='Transporter Company', required=True, help="The partner that is doing the delivery service.")
    product_id = fields.Many2one('product.product', string='Delivery Product', required=True, ondelete="cascade")
    price = fields.Float(compute='get_price')
    available = fields.Boolean(compute='get_price')
    free_if_more_than = fields.Boolean('Free if Order total is more than', help="If the order is more expensive than a certain amount, the customer can benefit from a free shipping", default=False)
    amount = fields.Float(string='Amount', help="Amount of the order to benefit from a free shipping, expressed in the company currency")
    country_ids = fields.Many2many('res.country', 'delivery_carrier_country_rel', 'carrier_id', 'country_id', 'Countries')
    state_ids = fields.Many2many('res.country.state', 'delivery_carrier_state_rel', 'carrier_id', 'state_id', 'States')
    zip_from = fields.Char('Zip From')
    zip_to = fields.Char('Zip To')
    price_rule_ids = fields.One2many('delivery.price.rule', 'carrier_id', 'Pricing Rules', copy=True)
    fixed_price = fields.Float(compute='_compute_fixed_price', inverse='_set_product_fixed_price', store=True, string='Fixed Price',help="Keep empty if the pricing depends on the advanced pricing per destination")
    shipping_enabled = fields.Boolean(string="Shipping enabled", default=True, help="Uncheck this box to disable package shipping while validating Delivery Orders")

    @api.multi
    def name_get(self):
        display_delivery = self.env.context.get('display_delivery', False)
        order_id = self.env.context.get('order_id', False)
        if display_delivery and order_id:
            order = self.env['sale.order'].browse(order_id)
            currency = order.pricelist_id.currency_id.name or ''
            res = []
            for carrier_id in self.ids:
                try:
                    r = self.read([carrier_id], ['name', 'price'])[0]
                    res.append((r['id'], r['name'] + ' (' + (str(r['price'])) + ' ' + currency + ')'))
                except ValidationError:
                    r = self.read([carrier_id], ['name'])[0]
                    res.append((r['id'], r['name']))
        else:
            res = super(DeliveryCarrier, self).name_get()
        return res

    @api.depends('product_id.list_price', 'product_id.product_tmpl_id.list_price')
    def _compute_fixed_price(self):
        for carrier in self:
            carrier.fixed_price = carrier.product_id.list_price

    def _set_product_fixed_price(self):
        for carrier in self:
            carrier.product_id.list_price = carrier.fixed_price

    @api.one
    def get_price(self):
        SaleOrder = self.env['sale.order']

        self.available = False
        self.price = False

        order_id = self.env.context.get('order_id')
        if order_id:
            # FIXME: temporary hack until we refactor the delivery API in master

            order = SaleOrder.browse(order_id)
            if self.delivery_type not in ['fixed', 'base_on_rule']:
                try:
                    self.price = self.get_shipping_price_from_so(order)[0]
                    self.available = True
                except UserError as e:
                    # No suitable delivery method found, probably configuration error
                    _logger.info("Carrier %s: %s, not found", self.name, e.name)
                    self.price = 0.0
            else:
                carrier = self.verify_carrier(order.partner_shipping_id)
                if carrier:
                    try:
                        self.price = carrier.get_price_available(order)
                        self.available = True
                    except UserError, e:
                        # No suitable delivery method found, probably configuration error
                        _logger.info("Carrier %s: %s", carrier.name, e.name)
                        self.price = 0.0
                else:
                    self.price = 0.0

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

    @api.onchange('state_ids')
    def onchange_states(self):
        self.country_ids = [(6, 0, self.country_ids.ids + self.state_ids.mapped('country_id.id'))]

    @api.onchange('country_ids')
    def onchange_countries(self):
        self.state_ids = [(6, 0, self.state_ids.filtered(lambda state: state.id in self.country_ids.mapped('state_ids').ids).ids)]

    @api.multi
    def verify_carrier(self, contact):
        self.ensure_one()
        if self.country_ids and contact.country_id not in self.country_ids:
            return False
        if self.state_ids and contact.state_id not in self.state_ids:
            return False
        if self.zip_from and (contact.zip or '') < self.zip_from:
            return False
        if self.zip_to and (contact.zip or '') > self.zip_to:
            return False
        return self

    @api.multi
    def create_price_rules(self):
        PriceRule = self.env['delivery.price.rule']
        for record in self:
            # If using advanced pricing per destination: do not change
            if record.delivery_type == 'base_on_rule':
                continue

            # Not using advanced pricing per destination: override lines
            if record.delivery_type == 'base_on_rule' and not (record.fixed_price is not False or record.free_if_more_than):
                record.price_rule_ids.unlink()

            # Check that float, else 0.0 is False
            if not (record.fixed_price is not False or record.free_if_more_than):
                continue

            if record.delivery_type == 'fixed':
                PriceRule.search([('carrier_id', '=', record.id)]).unlink()

                line_data = {
                    'carrier_id': record.id,
                    'variable': 'price',
                    'operator': '>=',
                }
                # Create the delivery price rules
                if record.free_if_more_than:
                    line_data.update({
                        'max_value': record.amount,
                        'standard_price': 0.0,
                        'list_base_price': 0.0,
                    })
                    PriceRule.create(line_data)
                if record.fixed_price is not False:
                    line_data.update({
                        'max_value': 0.0,
                        'standard_price': record.fixed_price,
                        'list_base_price': record.fixed_price,
                    })
                    PriceRule.create(line_data)
        return True

    @api.model
    def create(self, vals):
        res = super(DeliveryCarrier, self).create(vals)
        res.create_price_rules()
        return res

    @api.multi
    def write(self, vals):
        res = super(DeliveryCarrier, self).write(vals)
        self.create_price_rules()
        return res

    @api.multi
    def get_price_available(self, order):
        self.ensure_one()
        total = weight = volume = quantity = 0
        total_delivery = 0.0
        ProductUom = self.env['product.uom']
        for line in order.order_line:
            if line.state == 'cancel':
                continue
            if line.is_delivery:
                total_delivery += line.price_total
            if not line.product_id or line.is_delivery:
                continue
            qty = ProductUom._compute_qty(line.product_uom.id, line.product_uom_qty, line.product_id.uom_id.id)
            weight += (line.product_id.weight or 0.0) * qty
            volume += (line.product_id.volume or 0.0) * qty
            quantity += qty
        total = (order.amount_total or 0.0) - total_delivery

        total = order.currency_id.with_context(date=order.date_order).compute(total, order.company_id.currency_id)

        return self.get_price_from_picking(total, weight, volume, quantity)

    def get_price_from_picking(self, total, weight, volume, quantity):
        price = 0.0
        criteria_found = False
        price_dict = {'price': total, 'volume': volume, 'weight': weight, 'wv': volume * weight, 'quantity': quantity}
        for line in self.price_rule_ids:
            test = eval(line.variable + line.operator + str(line.max_value), price_dict)
            if test:
                price = line.list_base_price + line.list_price * price_dict[line.variable_factor]
                criteria_found = True
                break
        if not criteria_found:
            raise UserError(_("Selected product in the delivery method doesn't fulfill any of the delivery carrier(s) criteria."))

        return price
