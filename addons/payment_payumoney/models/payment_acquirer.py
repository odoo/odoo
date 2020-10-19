# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib

from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare

import logging

_logger = logging.getLogger(__name__)


class PaymentAcquirerPayumoney(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[
        ('payumoney', 'PayUmoney')
    ], ondelete={'payumoney': 'set default'})
    payumoney_merchant_key = fields.Char(string='Merchant Key', required_if_provider='payumoney', groups='base.group_user')
    payumoney_merchant_salt = fields.Char(string='Merchant Salt', required_if_provider='payumoney', groups='base.group_user')

    def _get_payumoney_urls(self, environment):
        """ PayUmoney URLs"""
        if environment == 'prod':
            return 'https://secure.payu.in/_payment'
        else:
            return 'https://sandboxsecure.payu.in/_payment'

    def _payumoney_generate_sign(self, inout, values):
        """ Generate the shasign for incoming or outgoing communications.
        :param self: the self browse record. It should have a shakey in shakey out
        :param string inout: 'in' (odoo contacting payumoney) or 'out' (payumoney
                             contacting odoo).
        :param dict values: transaction values

        :return string: shasign
        """
        if inout not in ('in', 'out'):
            raise Exception("Type must be 'in' or 'out'")

        if inout == 'in':
            keys = "key|txnid|amount|productinfo|firstname|email|udf1|||||||||".split('|')
            sign = ''.join('%s|' % (values.get(k) or '') for k in keys)
            sign += self.payumoney_merchant_salt or ''
        else:
            keys = "|status||||||||||udf1|email|firstname|productinfo|amount|txnid".split('|')
            sign = ''.join('%s|' % (values.get(k) or '') for k in keys)
            sign = self.payumoney_merchant_salt + sign + self.payumoney_merchant_key

        shasign = hashlib.sha512(sign.encode('utf-8')).hexdigest()
        return shasign

    def payumoney_get_redirect_action_url(self):
        self.ensure_one()
        environment = 'prod' if self.state == 'enabled' else 'test'
        return self._get_payumoney_urls(environment)

    @api.model
    def _get_compatible_acquirers(self, company_id, partner_id, currency_id=None, allow_tokenization=False, preferred_acquirer_id=None, **kwargs):
        acquirers = super()._get_compatible_acquirers(company_id, partner_id, currency_id, allow_tokenization, preferred_acquirer_id, **kwargs)

        inr_currency = self.env.ref('base.INR').id
        if currency_id != inr_currency:
            payu = self.search([('provider', '=', 'payumoney')])
            acquirers = acquirers - payu

        return acquirers
