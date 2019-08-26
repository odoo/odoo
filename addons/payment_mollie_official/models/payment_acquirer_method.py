# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


def get_base_url(env):
    base_url = env['ir.config_parameter'].sudo().get_param('web.base.url')
    return base_url


def get_mollie_provider(env):
    provider = env['payment.acquirer'].sudo()._get_main_mollie_provider()
    return provider


def get_mollie_provider_key(env):
    provider = env['payment.acquirer'].sudo()._get_main_mollie_provider()
    key = provider._get_mollie_api_keys(provider.state)['mollie_api_key']
    return key


class PaymentAcquirerMethod(models.Model):
    _name = 'payment.acquirer.method'
    _description = 'Mollie payment acquirer details'
    _order = 'sequence'

    name = fields.Char('Description', index=True,
                       required=True,
                       translate=True)
    sequence = fields.Integer(
        'Sequence', default=1,
        help='Gives the sequence order when displaying a method list')
    acquirer_id = fields.Many2one('payment.acquirer', 'Acquirer')
    acquirer_reference = fields.Char(
        string='Acquirer Reference',
        readonly=True,
        required=True,
        help='Reference of the order as stored in the acquirer database')
    image_small = fields.Binary(
        "Icon", attachment=True,
        help="Small-sized image of the method. It is automatically "
             "resized as a 64x64px image, with aspect ratio preserved. "
             "Use this field anywhere a small image is required.")
    currency_ids = fields.Many2many('res.currency',
                                    string='specific Currencies')
    country_ids = fields.Many2many('res.country',
                                   string='specific Countries')
    active = fields.Boolean(string='Active')

    def toggle_active(self):
        for record in self:
            record.active = not record.active
            if record.provider == 'mollie':
                key = get_mollie_provider_key(self.env)
                self._mollie_client.set_api_key(key)

                if record.active:
                    # Activates the payment method for your Mollie account (on mollie.com).
                    # Note: this only works when the payment acquirer Mollie is in 'production' and not in test mode.
                    self._mollie_client.profile_methods.with_parent_id('me', record.acquirer_reference).create()
                else:
                    # Deactivates the payment method for your Mollie account (on mollie.com).
                    # Note: this only works when the payment acquirer Mollie is in 'production' and not in test mode.
                    self._mollie_client.profile_methods.with_parent_id('me', record.acquirer_reference).delete()

