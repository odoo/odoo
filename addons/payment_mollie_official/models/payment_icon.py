# -*- coding: utf-8 -*-
from odoo import models, fields, api

from mollie.api.client import Client
from odoo.addons.payment_mollie_official.models.payment_acquirer_method import get_mollie_provider_key

# minimum and maximum amounts per payment method
DEFAULT_METHOD_VALUES = {
    'ideal': (0.01, 50000.00),
    'bancontact': (0.02, 50000.00),
    'belfius': (0.01, 50000.00),
    'kbc': (0.01, 50000.00),
    'inghomepay': (0.01, 50000.00),
    'creditcard': (0.01, 2000.00),
    'sofort': (0.01, 5000.00),
    'giropay': (1.0, 50000.00),
    'eps': (1.0, 10000.00),
    'banktransfer': (0.01, 1000.00),
    'paypal': (0.01, 8000.00),
    'bitcoin': (1, 15000.00),
    'klarnapaylater': (0.01, 2000.00),
    'klarnasliceit': (0.01, 2000.00),
    'paysafecard': (1, 999.00),
}


class PaymentIcon(models.Model):
    _inherit = 'payment.icon'
    _order = 'sequence'

    _mollie_client = Client()

    sequence = fields.Integer(
        'Sequence', default=1,
        help='Gives the sequence order when displaying a method list')
    provider = fields.Char(string='Provider')
    acquirer_reference = fields.Char(
        string='Acquirer Reference',
        readonly=True,
        help='Reference of the order as stored in the acquirer database')
    currency_ids = fields.Many2many('res.currency',
                                    string='specific Currencies')
    country_ids = fields.Many2many('res.country',
                                   string='specific Countries')
    name = fields.Char(translate=True)
    minimum_amount = fields.Float('Minimum amount',
                                  default=0.1,
                                  help='the minimum amount per payment method')
    maximum_amount = fields.Float('Maximum amount',
                                  default=50000.0,
                                  help='the maximum amount per payment method')

    @api.onchange('provider', 'acquirer_reference')
    def onchange_provider_ref(self):
        if self.provider == 'mollie' and self.acquirer_reference and\
                DEFAULT_METHOD_VALUES.get(
                self.acquirer_reference, False):
            self.minimum_amount = DEFAULT_METHOD_VALUES[
                self.acquirer_reference][0]
            self.maximum_amount = DEFAULT_METHOD_VALUES[
                self.acquirer_reference][1]
        else:
            self.minimum_amount = 0.01
            self.maximum_amount = 50000.0