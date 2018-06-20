# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import psycopg2

from odoo import api, fields, models, registry, SUPERUSER_ID, _

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _name = 'delivery.carrier'
    _description = "Carrier"
    _order = 'sequence, id'

    ''' A Shipping Provider

    In order to add your own external provider, follow these steps:

    1. Create your model MyProvider that _inherit 'delivery.carrier'
    2. Extend the selection of the field "delivery_type" with a pair
       ('<my_provider>', 'My Provider')
    3. Add your methods:
       <my_provider>_rate_shipment
       <my_provider>_send_shipping
       <my_provider>_get_tracking_link
       <my_provider>_cancel_shipment
       (they are documented hereunder)
    '''

    # -------------------------------- #
    # Internals for shipping providers #
    # -------------------------------- #

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(help="Determine the display order", default=10)
    # This field will be overwritten by internal shipping providers by adding their own type (ex: 'fedex')
    delivery_type = fields.Selection([('fixed', 'Fixed Price')], string='Provider', default='fixed', required=True)
    integration_level = fields.Selection([('rate', 'Get Rate'), ('rate_and_ship', 'Get Rate and Create Shipment')], string="Integration Level", default='rate_and_ship', help="Action while validating Delivery Orders")
    prod_environment = fields.Boolean("Environment", help="Set to True if your credentials are certified for production.")
    debug_logging = fields.Boolean('Debug logging', help="Log requests in order to ease debugging")
    company_id = fields.Many2one('res.company', string='Company', related='product_id.company_id', store=True)
    product_id = fields.Many2one('product.product', string='Delivery Product', required=True, ondelete='restrict')

    country_ids = fields.Many2many('res.country', 'delivery_carrier_country_rel', 'carrier_id', 'country_id', 'Countries')
    state_ids = fields.Many2many('res.country.state', 'delivery_carrier_state_rel', 'carrier_id', 'state_id', 'States')
    zip_from = fields.Char('Zip From')
    zip_to = fields.Char('Zip To')

    margin = fields.Integer(help='This percentage will be added to the shipping price.')
    free_over = fields.Boolean('Free if order amount is above', help="If the order total amount (shipping excluded) is above or equal to this value, the customer benefits from a free shipping", default=False, oldname='free_if_more_than')
    amount = fields.Float(string='Amount', help="Amount of the order to benefit from a free shipping, expressed in the company currency")

    _sql_constraints = [
        ('margin_not_under_100_percent', 'CHECK (margin >= -100)', 'Margin cannot be lower than -100%'),
    ]

    def toggle_prod_environment(self):
        for c in self:
            c.prod_environment = not c.prod_environment

    def toggle_debug(self):
        for c in self:
            c.debug_logging = not c.debug_logging

    @api.multi
    def install_more_provider(self):
        return {
            'name': 'New Providers',
            'view_mode': 'kanban',
            'res_model': 'ir.module.module',
            'domain': [['name', 'ilike', 'delivery_']],
            'type': 'ir.actions.act_window',
            'help': _('''<p class="oe_view_nocontent">
                    Buy Odoo Enterprise now to get more providers.
                </p>'''),
        }

    def available_carriers(self, partner):
        return self.filtered(lambda c: c._match_address(partner))

    def _match_address(self, partner):
        self.ensure_one()
        if self.country_ids and partner.country_id not in self.country_ids:
            return False
        if self.state_ids and partner.state_id not in self.state_ids:
            return False
        if self.zip_from and (partner.zip or '').upper() < self.zip_from.upper():
            return False
        if self.zip_to and (partner.zip or '').upper() > self.zip_to.upper():
            return False
        return True

    @api.onchange('state_ids')
    def onchange_states(self):
        self.country_ids = [(6, 0, self.country_ids.ids + self.state_ids.mapped('country_id.id'))]

    @api.onchange('country_ids')
    def onchange_countries(self):
        self.state_ids = [(6, 0, self.state_ids.filtered(lambda state: state.id in self.country_ids.mapped('state_ids').ids).ids)]

    # -------------------------- #
    # API for external providers #
    # -------------------------- #

    def rate_shipment(self, order):
        ''' Compute the price of the order shipment

        :param order: record of sale.order
        :return dict: {'success': boolean,
                       'price': a float,
                       'error_message': a string containing an error message,
                       'warning_message': a string containing a warning message}
                       # TODO maybe the currency code?
        '''
        self.ensure_one()
        if hasattr(self, '%s_rate_shipment' % self.delivery_type):
            res = getattr(self, '%s_rate_shipment' % self.delivery_type)(order)
            # apply margin on computed price
            res['price'] = res['price'] * (1.0 + (float(self.margin) / 100.0))
            # free when order is large enough
            if res['success'] and self.free_over and order._compute_amount_total_without_delivery() >= self.amount:
                res['warning_message'] = _('Info:\nThe shipping is free because the order amount exceeds %.2f.\n(The actual shipping cost is: %.2f)') % (self.amount, res['price'])
                res['price'] = 0.0
            return res

    def send_shipping(self, pickings):
        ''' Send the package to the service provider

        :param pickings: A recordset of pickings
        :return list: A list of dictionaries (one per picking) containing of the form::
                         { 'exact_price': price,
                           'tracking_number': number }
                           # TODO missing labels per package
                           # TODO missing currency
                           # TODO missing success, error, warnings
        '''
        self.ensure_one()
        if hasattr(self, '%s_send_shipping' % self.delivery_type):
            return getattr(self, '%s_send_shipping' % self.delivery_type)(pickings)

    def get_tracking_link(self, picking):
        ''' Ask the tracking link to the service provider

        :param picking: record of stock.picking
        :return str: an URL containing the tracking link or False
        '''
        self.ensure_one()
        if hasattr(self, '%s_get_tracking_link' % self.delivery_type):
            return getattr(self, '%s_get_tracking_link' % self.delivery_type)(picking)

    def cancel_shipment(self, pickings):
        ''' Cancel a shipment

        :param pickings: A recordset of pickings
        '''
        self.ensure_one()
        if hasattr(self, '%s_cancel_shipment' % self.delivery_type):
            return getattr(self, '%s_cancel_shipment' % self.delivery_type)(pickings)

    def log_xml(self, xml_string, func):
        self.ensure_one()

        if self.debug_logging:
            db_name = self._cr.dbname

            # Use a new cursor to avoid rollback that could be caused by an upper method
            try:
                db_registry = registry(db_name)
                with db_registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    IrLogging = env['ir.logging']
                    IrLogging.sudo().create({'name': 'delivery.carrier',
                              'type': 'server',
                              'dbname': db_name,
                              'level': 'DEBUG',
                              'message': xml_string,
                              'path': self.delivery_type,
                              'func': func,
                              'line': 1})
            except psycopg2.Error:
                pass

    # ------------------------------------------------ #
    # Fixed price shipping, aka a very simple provider #
    # ------------------------------------------------ #

    fixed_price = fields.Float(compute='_compute_fixed_price', inverse='_set_product_fixed_price', store=True, string='Fixed Price')

    @api.depends('product_id.list_price', 'product_id.product_tmpl_id.list_price')
    def _compute_fixed_price(self):
        for carrier in self:
            carrier.fixed_price = carrier.product_id.list_price

    def _set_product_fixed_price(self):
        for carrier in self:
            carrier.product_id.list_price = carrier.fixed_price

    def fixed_rate_shipment(self, order):
        price = self.fixed_price
        if self.company_id.currency_id.id != order.currency_id.id:
            price = self.env['res.currency']._compute(self.company_id.currency_id, order.currency_id, price)
        return {'success': True,
                'price': price,
                'error_message': False,
                'warning_message': False}

    def fixed_send_shipping(self, pickings):
        res = []
        for p in pickings:
            res = res + [{'exact_price': p.carrier_id.fixed_price,
                          'tracking_number': False}]
        return res

    def fixed_get_tracking_link(self, picking):
        return False

    def fixed_cancel_shipment(self, pickings):
        raise NotImplementedError()
