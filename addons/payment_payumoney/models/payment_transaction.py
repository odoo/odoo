# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib

from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare

import logging

_logger = logging.getLogger(__name__)

class PaymentTransactionPayumoney(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _get_tx_from_data(self, provider, data):
        """ Given a data dict coming from payumoney, verify it and find the related
        transaction record. """
        if provider != 'payumoney':
            return super()._get_tx_from_data(provider, data)

        reference = data.get('txnid')
        pay_id = data.get('mihpayid')
        shasign = data.get('hash')
        if not reference or not pay_id or not shasign:
            error_msg = _('PayUmoney: received data with missing reference (%(ref)s) or pay_id (%(id)s) or shasign (%(sha)s)',
                ref=reference, id=pay_id, sha=shasign)
            raise ValidationError(error_msg)

        transaction = self.search([('reference', '=', reference)])
        if not transaction:
            error_msg = _('PayUmoney: received data for reference %(ref)s; no order found', ref=reference)
            raise ValidationError(error_msg)
        elif len(transaction) > 1:
            error_msg = _('PayUmoney: received data for reference %(ref)s; multiple orders found', ref=reference)
            raise ValidationError(error_msg)

        # Verify shasign
        shasign_check = transaction.acquirer_id._payumoney_generate_sign('out', data)
        if shasign_check.upper() != shasign.upper():
            raise ValidationError(_('PayUmoney: invalid shasign, received %(sha)s, computed %(computed)s, for data %(data)s',
                sha=shasign, computed=shasign_check, data=data))
        return transaction

    def _get_invalid_parameters(self, data):
        if self.provider != "payumoney":
            return super()._get_invalid_parameters(data)

        invalid_parameters = {}
        if self.acquirer_reference and data.get('mihpayid') != self.acquirer_reference:
            invalid_parameters['TransactionId'] = (data.get('mihpayid'), self.acquirer_reference)

        # Check amounts are correct
        if float_compare(float(data.get('amount', '0.0')), self.amount, 2) != 0:
            invalid_parameters['Amount'] = (data.get('amount'), '%.2f' % self.amount)

        return invalid_parameters

    def _process_feedback_data(self, data):
        if self.provider != "payumoney":
            return super()._process_feedback_data(data)

        status = data.get('status')
        result = dict(acquirer_reference=data.get('payuMoneyId'))

        if status == 'success':
            self._set_done()
        elif status == 'pending':
            self._set_pending()
            result['state_message'] = data.get('error_Message') or data.get('field9') or ''
        else:
            self._set_canceled()
            result['state_message'] = data.get('field9') or ''

        return self.write(result)

    def _get_specific_processing_values(self, processing_values):
        self.ensure_one()
        if self.provider != 'payumoney':
            return super()._get_specific_processing_values(processing_values)

        base_url = self.get_base_url()
        payumoney_values = dict(processing_values,
                                key=self.acquirer_id.payumoney_merchant_key,
                                txnid=processing_values['reference'],
                                amount=processing_values.get('amount'),
                                productinfo=processing_values['reference'],
                                firstname=processing_values.get('partner_name'),
                                email=processing_values.get('partner_email'),
                                phone=processing_values.get('partner_phone'),
                                service_provider='payu_paisa',
                                surl=urls.url_join(base_url, '/payment/payumoney/success'), # Success URL
                                furl=urls.url_join(base_url, '/payment/payumoney/failure'), # Failure URL
                                )

        payumoney_values['udf1'] = payumoney_values.pop('return_url', '/') # User defined field 1
        payumoney_values['hash'] = self.acquirer_id._payumoney_generate_sign('in', payumoney_values)
        return payumoney_values

    def _get_specific_rendering_values(self, processing_values):
        self.ensure_one()
        if self.provider != "payumoney":
            return super()._get_specific_rendering_values(processing_values)

        processing_values['redirect_url'] = self.acquirer_id.payumoney_get_redirect_action_url()
        return processing_values
