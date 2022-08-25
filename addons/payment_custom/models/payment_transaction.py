# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_custom.controllers.main import CustomController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return custom-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != 'custom':
            return res

        return {
            'api_url': CustomController._process_url,
            'reference': self.reference,
        }

    def _get_tx_from_notification_data(self, provider, notification_data):
        """ Override of payment to find the transaction based on custom data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict notification_data: The notification feedback data
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider, notification_data)
        if provider != 'custom' or len(tx) == 1:
            return tx

        reference = notification_data.get('reference')
        tx = self.search([('reference', '=', reference), ('provider', '=', 'custom')])
        if not tx:
            raise ValidationError(
                "Wire Transfer: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on custom data.

        Note: self.ensure_one()

        :param dict notification_data: The custom data
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider != 'custom':
            return

        _logger.info(
            "validated custom payment for transaction with reference %s: set as pending",
            self.reference
        )
        self._set_pending()

    def _log_received_message(self):
        """ Override of `payment` to remove custom acquirers from the recordset.

        :return: None
        """
        other_provider_txs = self.filtered(lambda t: t.provider != 'custom')
        super(PaymentTransaction, other_provider_txs)._log_received_message()

    def _get_sent_message(self):
        """ Override of payment to return a different message.

        :return: The 'transaction sent' message
        :rtype: str
        """
        message = super()._get_sent_message()
        if self.provider == 'custom':
            message = _(
                "The customer has selected %(acq_name)s to make the payment.",
                acq_name=self.acquirer_id.name
            )
        return message
