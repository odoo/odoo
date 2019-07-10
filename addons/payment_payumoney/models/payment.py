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

    provider = fields.Selection(selection_add=[('payumoney', 'PayUmoney')])
    payumoney_merchant_key = fields.Char(string='Merchant Key', required_if_provider='payumoney', groups='base.group_user')
    payumoney_merchant_salt = fields.Char(string='Merchant Salt', required_if_provider='payumoney', groups='base.group_user')

    def _get_payumoney_urls(self, environment):
        """ PayUmoney URLs"""
        if environment == 'prod':
            return {'payumoney_form_url': 'https://secure.payu.in/_payment'}
        else:
            return {'payumoney_form_url': 'https://test.payu.in/_payment'}

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

    def payumoney_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        payumoney_values = dict(values,
                                key=self.payumoney_merchant_key,
                                txnid=values['reference'],
                                amount=values['amount'],
                                productinfo=values['reference'],
                                firstname=values.get('partner_name'),
                                email=values.get('partner_email'),
                                phone=values.get('partner_phone'),
                                service_provider='payu_paisa',
                                surl=urls.url_join(base_url, '/payment/payumoney/return'),
                                furl=urls.url_join(base_url, '/payment/payumoney/error'),
                                curl=urls.url_join(base_url, '/payment/payumoney/cancel')
                                )

        payumoney_values['udf1'] = payumoney_values.pop('return_url', '/')
        payumoney_values['hash'] = self._payumoney_generate_sign('in', payumoney_values)
        return payumoney_values

    def payumoney_get_form_action_url(self):
        self.ensure_one()
        return self._get_payumoney_urls(self.environment)['payumoney_form_url']


class PaymentTransactionPayumoney(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _payumoney_form_get_tx_from_data(self, data):
        """ Given a data dict coming from payumoney, verify it and find the related
        transaction record. """
        reference = data.get('txnid')
        pay_id = data.get('mihpayid')
        shasign = data.get('hash')
        if not reference or not pay_id or not shasign:
            raise ValidationError(_('PayUmoney: received data with missing reference (%s) or pay_id (%s) or shashign (%s)') % (reference, pay_id, shasign))

        transaction = self.search([('reference', '=', reference)])

        if not transaction:
            error_msg = (_('PayUmoney: received data for reference %s; no order found') % (reference))
            raise ValidationError(error_msg)
        elif len(transaction) > 1:
            error_msg = (_('PayUmoney: received data for reference %s; multiple orders found') % (reference))
            raise ValidationError(error_msg)

        #verify shasign
        shasign_check = transaction.acquirer_id._payumoney_generate_sign('out', data)
        if shasign_check.upper() != shasign.upper():
            raise ValidationError(_('PayUmoney: invalid shasign, received %s, computed %s, for data %s') % (shasign, shasign_check, data))
        return transaction

    def _payumoney_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        if self.acquirer_reference and data.get('mihpayid') != self.acquirer_reference:
            invalid_parameters.append(
                ('Transaction Id', data.get('mihpayid'), self.acquirer_reference))
        #check what is buyed
        if float_compare(float(data.get('amount', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(
                ('Amount', data.get('amount'), '%.2f' % self.amount))

        return invalid_parameters

    def _payumoney_form_validate(self, data):
        status = data.get('status')
        result = self.write({
            'acquirer_reference': data.get('payuMoneyId'),
            'date': fields.Datetime.now(),
        })
        if status == 'success':
            self._set_transaction_done()
        elif status != 'pending':
            self._set_transaction_cancel()
        else:
            self._set_transaction_pending()
        return result
