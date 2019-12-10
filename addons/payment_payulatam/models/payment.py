# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import uuid

from hashlib import md5
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare


_logger = logging.getLogger(__name__)


class PaymentAcquirerPayulatam(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('payulatam', 'PayU Latam')])
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

    def payulatam_form_generate_values(self, values):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        tx = self.env['payment.transaction'].search([('reference', '=', values.get('reference'))])
        # payulatam will not allow any payment twise even if payment was failed last time.
        # so, replace reference code if payment is not done or pending.
        if tx.state not in ['done', 'pending']:
            tx.reference = str(uuid.uuid4())
        payulatam_values = dict(
            values,
            merchantId=self.payulatam_merchant_id,
            accountId=self.payulatam_account_id,
            description=values.get('reference'),
            referenceCode=tx.reference,
            amount=values['amount'],
            tax='0',  # This is the transaction VAT. If VAT zero is sent the system, 19% will be applied automatically. It can contain two decimals. Eg 19000.00. In the where you do not charge VAT, it should should be set as 0.
            taxReturnBase='0',
            currency=values['currency'].name,
            buyerEmail=values['partner_email'],
            responseUrl=urls.url_join(base_url, '/payment/payulatam/response'),
        )
        payulatam_values['signature'] = self._payulatam_generate_sign("in", payulatam_values)
        return payulatam_values

    def payulatam_get_form_action_url(self):
        self.ensure_one()
        environment = 'prod' if self.state == 'enabled' else 'test'
        return self._get_payulatam_urls(environment)


class PaymentTransactionPayulatam(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _payulatam_form_get_tx_from_data(self, data):
        """ Given a data dict coming from payulatam, verify it and find the related
        transaction record. """
        reference, txnid, sign = data.get('referenceCode'), data.get('transactionId'), data.get('signature')
        if not reference or not txnid or not sign:
            raise ValidationError(_('PayU Latam: received data with missing reference (%s) or transaction id (%s) or sign (%s)') % (reference, txnid, sign))

        transaction = self.search([('reference', '=', reference)])

        if not transaction:
            error_msg = (_('PayU Latam: received data for reference %s; no order found') % (reference))
            raise ValidationError(error_msg)
        elif len(transaction) > 1:
            error_msg = (_('PayU Latam: received data for reference %s; multiple orders found') % (reference))
            raise ValidationError(error_msg)

        # verify shasign
        sign_check = transaction.acquirer_id._payulatam_generate_sign('out', data)
        if sign_check.upper() != sign.upper():
            raise ValidationError(('PayU Latam: invalid sign, received %s, computed %s, for data %s') % (sign, sign_check, data))
        return transaction

    def _payulatam_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        if self.acquirer_reference and data.get('transactionId') != self.acquirer_reference:
            invalid_parameters.append(('Reference code', data.get('transactionId'), self.acquirer_reference))
        if float_compare(float(data.get('TX_VALUE', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(('Amount', data.get('TX_VALUE'), '%.2f' % self.amount))
        if data.get('merchantId') != self.acquirer_id.payulatam_merchant_id:
            invalid_parameters.append(('Merchant Id', data.get('merchantId'), self.acquirer_id.payulatam_merchant_id))
        return invalid_parameters

    def _payulatam_form_validate(self, data):
        self.ensure_one()

        status = data.get('lapTransactionState') or data.find('transactionResponse').find('state').text
        res = {
            'acquirer_reference': data.get('transactionId') or data.find('transactionResponse').find('transactionId').text,
            'state_message': data.get('message') or ""
        }

        if status == 'APPROVED':
            _logger.info('Validated PayU Latam payment for tx %s: set as done' % (self.reference))
            res.update(state='done', date=fields.Datetime.now())
            self._set_transaction_done()
            self.write(res)
            self.execute_callback()
            return True
        elif status == 'PENDING':
            _logger.info('Received notification for PayU Latam payment %s: set as pending' % (self.reference))
            res.update(state='pending')
            self._set_transaction_pending()
            return self.write(res)
        elif status in ['EXPIRED', 'DECLINED']:
            _logger.info('Received notification for PayU Latam payment %s: set as Cancel' % (self.reference))
            res.update(state='cancel')
            self._set_transaction_cancel()
            return self.write(res)
        else:
            error = 'Received unrecognized status for PayU Latam payment %s: %s, set as error' % (self.reference, status)
            _logger.info(error)
            res.update(state='cancel', state_message=error)
            self._set_transaction_cancel()
            return self.write(res)
