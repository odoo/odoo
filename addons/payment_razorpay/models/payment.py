# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare, float_repr, float_round
from odoo.addons.payment.models.payment_acquirer import ValidationError

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('razorpay', 'Razorpay')])
    razorpay_key_id = fields.Char(string='Key ID', required_if_provider='razorpay', groups='base.group_user')
    razorpay_key_secret = fields.Char(string='Key Secret', required_if_provider='razorpay', groups='base.group_user')

    @api.multi
    def razorpay_form_generate_values(self, values):
        self.ensure_one()
        currency = self.env['res.currency'].sudo().browse(values['currency_id'])
        if currency != self.env.ref('base.INR'):
            raise ValidationError(_('Currency not supported by Razorpay'))
        values.update({
            'key': self.razorpay_key_id,
            'amount': float_repr(float_round(values.get('amount'), 2) * 100, 0),
            'name': values.get('partner_name'),
            'contact': values.get('partner_phone'),
            'email': values.get('partner_email'),
            'order_id': values.get('reference'),
        })
        return values


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _create_razorpay_capture(self, data):
        payment_acquirer = self.env['payment.acquirer'].search([('provider', '=', 'razorpay')], limit=1)
        payment_url = "https://%s:%s@api.razorpay.com/v1/payments/%s" % (payment_acquirer.razorpay_key_id, payment_acquirer.razorpay_key_secret, data.get('payment_id'))
        try:
            payment_response = requests.get(payment_url)
            payment_response = payment_response.json()
        except Exception as e:
            raise e
        reference = payment_response.get('notes', {}).get('order_id', False)
        if reference:
            transaction = self.search([('reference', '=', reference)])
            capture_url = "https://%s:%s@api.razorpay.com/v1/payments/%s/capture" % (payment_acquirer.razorpay_key_id, payment_acquirer.razorpay_key_secret, data.get('payment_id'))
            charge_data = {'amount': int(transaction.amount * 100)}
            try:
                payment_response = requests.post(capture_url, data=charge_data)
                payment_response = payment_response.json()
            except Exception as e:
                raise e
        return payment_response

    @api.model
    def _razorpay_form_get_tx_from_data(self, data):
        reference, txn_id = data.get('notes', {}).get('order_id'), data.get('id')
        if not reference or not txn_id:
            error_msg = _('Razorpay: received data with missing reference (%s) or txn_id (%s)') % (reference, txn_id)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        txs = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = _('Razorpay: received data for reference %s') % (reference)
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return txs[0]

    @api.multi
    def _razorpay_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        if float_compare(data.get('amount', '0.0') / 100, self.amount, precision_digits=2) != 0:
            invalid_parameters.append(('amount', data.get('amount'), '%.2f' % self.amount))
        return invalid_parameters

    @api.multi
    def _razorpay_form_validate(self, data):
        status = data.get('status')
        if status == 'captured':
            _logger.info('Validated Razorpay payment for tx %s: set as done' % (self.reference))
            self.write({'acquirer_reference': data.get('id')})
            self._set_transaction_done()
            return True
        if status == 'authorized':
            _logger.info('Validated Razorpay payment for tx %s: set as authorized' % (self.reference))
            self.write({'acquirer_reference': data.get('id')})
            self._set_transaction_authorized()
            return True
        else:
            error = 'Received unrecognized status for Razorpay payment %s: %s, set as error' % (self.reference, status)
            _logger.info(error)
            self.write({'acquirer_reference': data.get('id'), 'state_message': data.get('error')})
            self._set_transaction_cancel()
            return False
