# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo.exceptions import ValidationError, UserError
from odoo.addons.payment_xendit.const import STATUS_MAPPING
from odoo import models

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Override of `payment` to find the transaction based on the data

        :param str provider_code: code that handles the transaction
        :param dict notification_data: 'normalized' notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'xendit' or len(tx) == 1:
            return tx

        ref = notification_data.get('external_id', '')
        if ref:
            tx = self.search([('reference', '=', ref), ('provider_code', '=', 'xendit')])
        elif notification_data.get('event') in ('refund.succeeded', 'refund.failed'):
            refund_id = notification_data.get('data', {}).get('id')
            tx = self.search([('provider_reference', '=', refund_id), ('provider_code', '=', 'xendit')])
        else:
            _logger.exception("Un-recognised notification data: %s", notification_data)

        if not tx:
            raise ValidationError("Xendit: No Transaction found for matching reference %s" % ref)

        _logger.info("Found Xendit transaction: %s", tx)
        return tx

    def _process_notification_data(self, notification_data):
        """Override of `payment` to process the transaction based on Razorpay data

        Depending on the data, get the status from data and update status of transaction accordingly
        If payment is done through credit card on the payment page, notification_data should include 'credit_card_token' information,
        which we will store internally and used for charges in the future
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'xendit':
            return

        # payment status is either PAID or EXPIRED
        payment_status = notification_data.get('status')
        if not self.provider_reference and payment_status in (STATUS_MAPPING['done'] + STATUS_MAPPING['pending'] + STATUS_MAPPING['authorized']) and notification_data.get('id'):
            self.provider_reference = notification_data.get('id')

        if payment_status in STATUS_MAPPING['done']:
            if self.tokenize and notification_data.get('credit_card_token'):
                self._xendit_tokenize_notification_data(notification_data)
            self._set_done()
        elif payment_status in STATUS_MAPPING['pending']:
            self._set_pending()
        elif payment_status in STATUS_MAPPING['authorized']:
            self._set_authorized()
        elif payment_status in STATUS_MAPPING['cancel']:
            self._set_canceled()
        elif payment_status in STATUS_MAPPING['error']:
            self._set_error()

    def _xendit_tokenize_notification_data(self, notification_data):
        """ Creating a new token based on the notification data.

        :param dict notification_data: notification data sent by Xendit after transaction"""
        token_data = notification_data.get('credit_card_token')
        response = self.provider_id._xendit_make_request('TOKEN', endpoint_param={'token_id': token_data}, method='GET')
        card_info = response.get('masked_card_number')[-4:]

        _logger.info("Creating token for card: %s", token_data)
        token = self.env['payment.token'].create({
            'provider_id': self.provider_id.id,
            'payment_method_id': self.payment_method_id.id,
            'payment_details': card_info,
            'partner_id': self.partner_id.id,
            'provider_ref': token_data,
            # 'verified': True,
        })
        self.write({
            'token_id': token,
            'tokenize': False,
        })

    def _send_payment_request(self):
        """ Override of `payment` to send a payment request to Xendit (credit cards)

        :return None
        """
        super()._send_payment_request()
        if self.provider_code != 'xendit':
            return
        if not self.token_id:
            raise UserError("Transaction is not linked to a token")

        payload = {
            "token_id": self.token_id.provider_ref,
            "external_id": self.reference,
            "amount": self.amount,
        }

        charge_res = self.provider_id._xendit_make_request('CHARGE', payload=payload)

        # check statuses
        self._handle_notification_data('xendit', charge_res)

    def _send_refund_request(self, amount_to_refund=None):
        """ Override of `payment` to handle refund procedure to Xendit (available for multiple things)
        """

        refund_tx = super()._send_refund_request(amount_to_refund)
        if self.provider_code != 'xendit':
            return refund_tx

        # tokenized and non-tokenized payment will call different API from xendit
        if self.token_id:
            payload = {
                "amount": -refund_tx.amount,
                "external_id": refund_tx.reference
            }
            data = self.provider_id._xendit_make_request('CARD_REFUND', payload=payload, endpoint_param={'charge_id': self.provider_reference})
        else:
            payload = {
                "invoice_id": self.provider_reference,
                "reason": "OTHERS",
                "amount": -refund_tx.amount,
            }
            data = self.provider_id._xendit_make_request('REFUND', payload=payload)
        _logger.info("Refund request response for transaction %s: %s", self.reference, data)

        refund_tx._handle_notification_data('xendit', data)
        return refund_tx
