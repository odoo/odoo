# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from hashlib import md5

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
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

    #=== COMPUTE METHODS ===#

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda acq: acq.provider == 'alipay').update({
            'support_fees': True,
        })

    # === BUSINESS METHODS ===#

    @api.model
    def _get_compatible_acquirers(self, *args, currency_id=None, **kwargs):
        """ Override of payment to unlist Alipay acquirers for unsupported currencies. """
        acquirers = super()._get_compatible_acquirers(*args, currency_id=currency_id, **kwargs)

        currency = self.env['res.currency'].browse(currency_id).exists()
        if currency and currency.name != 'CNY':
            acquirers = acquirers.filtered(
                lambda a: a.provider != 'alipay' or a.alipay_payment_method != 'express_checkout'
            )

        return acquirers

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

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'alipay':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_alipay.payment_method_alipay').id

    def _neutralize(self):
        super()._neutralize()
        self._neutralize_fields('alipay', [
            'alipay_merchant_partner_id',
            'alipay_md5_signature_key',
            'alipay_seller_email',
        ])
