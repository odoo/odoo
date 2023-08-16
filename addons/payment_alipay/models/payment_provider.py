# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from hashlib import md5

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('alipay', "Alipay")], ondelete={'alipay': 'set default'})
    alipay_payment_method = fields.Selection(
        string="Account",
        selection=[
            ('express_checkout', 'Express Checkout (only for Chinese merchants)'),
            ('standard_checkout', 'Cross-border')
        ], default='express_checkout', required_if_provider='alipay')
    alipay_merchant_partner_id = fields.Char(
        string="Merchant Partner ID",
        help="The public partner ID solely used to identify the account with Alipay",
        required_if_provider='alipay')
    alipay_md5_signature_key = fields.Char(
        string="MD5 Signature Key", required_if_provider='alipay', groups='base.group_system')
    alipay_seller_email = fields.Char(
        string="Alipay Seller Email", help="The public Alipay partner email")

    # === BUSINESS METHODS ===#

    @api.model
    def _get_compatible_providers(self, *args, currency_id=None, **kwargs):
        """ Override of payment to unlist Alipay providers when the currency is not CNY in case of
        express checkout. """
        providers = super()._get_compatible_providers(*args, currency_id=currency_id, **kwargs)

        currency = self.env['res.currency'].browse(currency_id).exists()
        if currency and currency.name != 'CNY':
            providers = providers.filtered(
                lambda p: p.code != 'alipay' or p.alipay_payment_method != 'express_checkout'
            )

        return providers

    def _alipay_compute_signature(self, data):
        # Rearrange parameters in the data set alphabetically
        data_to_sign = sorted(data.items())
        # Format key-value pairs of parameters that should be signed
        data_to_sign = [f"{k}={v}" for k, v in data_to_sign
                        if k not in ['sign', 'sign_type', 'reference']]
        # Build the data string of &-separated key-value pairs
        data_string = '&'.join(data_to_sign)
        data_string += self.alipay_md5_signature_key
        return md5(data_string.encode('utf-8')).hexdigest()

    def _alipay_get_api_url(self):
        if self.state == 'enabled':
            return 'https://mapi.alipay.com/gateway.do'
        else:  # test environment
            return 'https://openapi.alipaydev.com/gateway.do'
