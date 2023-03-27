# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo.exceptions import ValidationError
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
