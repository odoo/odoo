# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import uuid

from hashlib import md5
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare


_logger = logging.getLogger(__name__)

PAYULATAM_SUPPORTED_CURRENCIES = ['ARS', 'BRL', 'CLP', 'COP', 'MXN', 'PEN', 'USD']


class PaymentAcquirerPayulatam(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[
        ('payulatam', 'PayU Latam')
    ], ondelete={'payulatam': 'set default'})
    payulatam_merchant_id = fields.Char(string="PayU Latam Merchant ID", required_if_provider='payulatam', groups='base.group_user')
    payulatam_account_id = fields.Char(string="PayU Latam Account ID", required_if_provider='payulatam', groups='base.group_user')
    payulatam_api_key = fields.Char(string="PayU Latam API Key", required_if_provider='payulatam', groups='base.group_user')

    def _get_payulatam_urls(self, environment):
        """ PayUlatam URLs"""
        if environment == 'prod':
            return 'https://checkout.payulatam.com/ppp-web-gateway-payu/'
        return 'https://sandbox.checkout.payulatam.com/ppp-web-gateway-payu/'

    def _payulatam_generate_sign(self, inout, values):
        if inout not in ('in', 'out'):
            raise Exception("Type must be 'in' or 'out'")

        if inout == 'in':
            data_string = ('~').join((self.payulatam_api_key, self.payulatam_merchant_id, values['referenceCode'],
                                      str(values['amount']), values['currency']))
        else:
            data_string = ('~').join((self.payulatam_api_key, self.payulatam_merchant_id, values['referenceCode'],
                                      str(float(values.get('TX_VALUE'))), values['currency'], values.get('transactionState')))
        return md5(data_string.encode('utf-8')).hexdigest()

    def payulatam_get_redirect_action_url(self):
        self.ensure_one()
        environment = 'prod' if self.state == 'enabled' else 'test'
        return self._get_payulatam_urls(environment)

    @api.model
    def _get_compatible_acquirers(self, company_id, partner_id, currency_id=None, allow_tokenization=False, preferred_acquirer_id=None, **kwargs):
        acquirers = super()._get_compatible_acquirers(company_id, partner_id, currency_id, allow_tokenization, preferred_acquirer_id, **kwargs)

        supported_currencies = self.env['res.currency'].search([('name', 'in', PAYULATAM_SUPPORTED_CURRENCIES)])
        if currency_id not in supported_currencies.ids:
            payu = self.search([('provider', '=', 'payulatam')])
            acquirers = acquirers - payu

        return acquirers
