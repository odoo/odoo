# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, models
from odoo.exceptions import ValidationError

from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _send_payment_request(self):
        """ Override of payment to simulate a payment request.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_payment_request()
        if self.provider != 'test':
            return

        # The payment request response would normally transit through the controller but in the end,
        # all that interests us is the reference. To avoid making a localhost request, we bypass the
        # controller and handle the fake feedback data directly.
        self._handle_feedback_data('test', {'reference': self.reference})

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        """ Override of payment to find the transaction based on dummy data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The dummy feedback data
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != 'test':
            return tx

        reference = data.get('reference')
        tx = self.search([('reference', '=', reference), ('provider', '=', 'test')])
        if not tx:
            raise ValidationError(
                "Test: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_feedback_data(self, data):
        """ Override of payment to process the transaction based on dummy data.

        Note: self.ensure_one()

        :param dict data: The dummy feedback data
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_feedback_data(data)
        if self.provider != "test":
            return

        self._set_done()  # Dummy transactions are always successful
        if self.tokenize:
            token = self.env['payment.token'].create({
                'acquirer_id': self.acquirer_id.id,
                'name': payment_utils.build_token_name(payment_details_short=data['cc_summary']),
                'partner_id': self.partner_id.id,
                'acquirer_ref': 'fake acquirer reference',
                'verified': True,
            })
            self.token_id = token.id
