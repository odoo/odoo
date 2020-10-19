# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from werkzeug import urls

from odoo import api, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment.utils import singularize_reference_prefix
from odoo.tools.float_utils import float_compare, float_repr


_logger = logging.getLogger(__name__)


class PaymentTransactionPayulatam(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _compute_reference(self, provider, prefix=None, separator="-", **kwargs):
        if provider == 'payulatam':
            prefix = singularize_reference_prefix(separator='')
        return super()._compute_reference(provider, prefix, separator, **kwargs)

    @api.model
    def _get_tx_from_data(self, provider, data):
        """ Given a data dict coming from payulatam, verify it and find the related
        transaction record. """
        if provider != 'payulatam':
            return super()._get_tx_from_data(provider, data)

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

    def _get_invalid_parameters(self, data):
        if self.provider != "payulatam":
            return super()._get_invalid_parameters(data)

        invalid_parameters = {}
        if self.acquirer_reference and data.get('transactionId') != self.acquirer_reference:
            invalid_parameters['Reference code'] = (data.get('transactionId'), self.acquirer_reference)
        if float_compare(float(data.get('TX_VALUE', '0.0')), self.amount, 2) != 0:
            invalid_parameters['Amount'] = (data.get('TX_VALUE'), '%.2f' % self.amount)
        if data.get('merchantId') != self.acquirer_id.payulatam_merchant_id:
            invalid_parameters['Merchant Id'] = (data.get('merchantId'), self.acquirer_id.payulatam_merchant_id)
        return invalid_parameters

    def _process_feedback_data(self, data):
        self.ensure_one()
        if self.provider != "payulatam":
            return super()._process_feedback_data(data)

        status = data.get('lapTransactionState') or data.find('transactionResponse').find('state').text
        res = {
            'acquirer_reference': data.get('transactionId') or data.find('transactionResponse').find('transactionId').text,
            'state_message': data.get('message') or ""
        }

        if status == 'APPROVED':
            _logger.info('Validated PayU Latam payment for tx %s: set as done' % (self.reference))
            self._set_done()
        elif status == 'PENDING':
            _logger.info('Received notification for PayU Latam payment %s: set as pending' % (self.reference))
            self._set_pending()
        elif status in ['EXPIRED', 'DECLINED']:
            _logger.info('Received notification for PayU Latam payment %s: set as cancel' % (self.reference))
            self._set_canceled()
        else:
            error = 'Received unrecognized status for PayU Latam payment %s: %s, set as error' % (self.reference, status)
            _logger.info(error)
            self._set_canceled()
        return self.write(res)

    def _get_specific_processing_values(self, processing_values):
        self.ensure_one()
        if self.provider != "payulatam":
            return super()._get_specific_rendering_values(processing_values)

        currency = self.env['res.currency'].browse(processing_values.get('currency_id'))
        partner = self.env['res.partner']
        if processing_values.get('partner_id'):
            partner = self.env['res.partner'].browse(processing_values.get('partner_id'))

        payulatam_values = dict(
            processing_values,
            merchantId=self.acquirer_id.payulatam_merchant_id,
            accountId=self.acquirer_id.payulatam_account_id,
            description=processing_values.get('reference'),
            referenceCode=processing_values.get('reference'),
            amount=float_repr(processing_values['amount'], currency.decimal_places or 2),
            tax='0', # This is the transaction VAT. If VAT zero is sent the system, 19% will be applied automatically. It can contain two decimals. Eg 19000.00. In the where you do not charge VAT, it should should be set as 0.
            taxReturnBase='0',
            currency=currency.name,
            buyerEmail=partner.email,
            buyerFullName=partner.name,
            responseUrl=urls.url_join(self.get_base_url(), '/payment/payulatam/response'),
        )

        if self.acquirer_id.state != 'enabled':
            payulatam_values['test'] = 1
        payulatam_values['signature'] = self.acquirer_id._payulatam_generate_sign("in", payulatam_values)
        return payulatam_values

    def _get_specific_rendering_values(self, processing_values):
        self.ensure_one()
        if self.provider != "payulatam":
            return super()._get_specific_rendering_values(processing_values)

        processing_values['redirect_url'] = self.acquirer_id.payulatam_get_redirect_action_url()
        return processing_values
