# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare


_logger = logging.getLogger(__name__)


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

    @api.model
    def _payumoney_form_get_invalid_parameters(self, transaction, data):
        invalid_parameters = []

        if transaction.acquirer_reference and data.get('mihpayid') != transaction.acquirer_reference:
            invalid_parameters.append(
                ('Transaction Id', data.get('mihpayid'), transaction.acquirer_reference))
        #check what is buyed
        if float_compare(float(data.get('amount', '0.0')), transaction.amount, 2) != 0:
            invalid_parameters.append(
                ('Amount', data.get('amount'), '%.2f' % transaction.amount))

        return invalid_parameters

    @api.model
    def _payumoney_form_validate(self, transaction, data):
        status = data.get('status')
        transaction_status = {
            'success': {
                'state': 'done',
                'acquirer_reference': data.get('payuMoneyId'),
                'date_validate': fields.Datetime.now(),
            },
            'pending': {
                'state': 'pending',
                'acquirer_reference': data.get('payuMoneyId'),
                'date_validate': fields.Datetime.now(),
            },
            'failure': {
                'state': 'cancel',
                'acquirer_reference': data.get('payuMoneyId'),
                'date_validate': fields.Datetime.now(),
            },
            'error': {
                'state': 'error',
                'state_message': data.get('error_Message') or _('PayUmoney: feedback error'),
                'acquirer_reference': data.get('payuMoneyId'),
                'date_validate': fields.Datetime.now(),
            }
        }
        vals = transaction_status.get(status, False)
        if not vals:
            vals = transaction_status['error']
            _logger.info(vals['state_message'])
        return transaction.write(vals)
