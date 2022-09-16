# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    capture_manually = fields.Boolean(related='provider_id.capture_manually')

    #=== ACTION METHODS ===#

    def action_demo_set_done(self):
        """ Set the state of the demo transaction to 'done'.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.provider_code != 'demo':
            return

        notification_data = {'reference': self.reference, 'simulated_state': 'done'}
        self._handle_notification_data('demo', notification_data)

    def action_demo_set_canceled(self):
        """ Set the state of the demo transaction to 'cancel'.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.provider_code != 'demo':
            return

        notification_data = {'reference': self.reference, 'simulated_state': 'cancel'}
        self._handle_notification_data('demo', notification_data)

    def action_demo_set_error(self):
        """ Set the state of the demo transaction to 'error'.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.provider_code != 'demo':
            return

        notification_data = {'reference': self.reference, 'simulated_state': 'error'}
        self._handle_notification_data('demo', notification_data)

    #=== BUSINESS METHODS ===#

    def _send_payment_request(self):
        """ Override of payment to simulate a payment request.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_payment_request()
        if self.provider_code != 'demo':
            return

        if not self.token_id:
            raise UserError("Demo: " + _("The transaction is not linked to a token."))

        simulated_state = self.token_id.demo_simulated_state
        notification_data = {'reference': self.reference, 'simulated_state': simulated_state}
        self._handle_notification_data('demo', notification_data)

    def _send_refund_request(self, create_refund_transaction=True, **kwargs):
        """ Override of payment to simulate a refund.

        Note: self.ensure_one()

        :param bool create_refund_transaction: Whether a refund transaction should be created.
        :param dict kwargs: The keyword arguments.
        :return: The refund transaction if any
        :rtype: recordset of `payment.transaction`
        """
        if self.provider_code != 'demo':
            return super()._send_refund_request(
                create_refund_transaction=create_refund_transaction, **kwargs
            )
        refund_tx = super()._send_refund_request(create_refund_transaction=True, **kwargs)

        notification_data = {'reference': refund_tx.reference, 'simulated_state': 'done'}
        refund_tx._handle_notification_data('demo', notification_data)

        return refund_tx

    def _send_capture_request(self):
        """ Override of payment to simulate a capture request.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_capture_request()
        if self.provider_code != 'demo':
            return

        notification_data = {
            'reference': self.reference,
            'simulated_state': 'done',
            'manual_capture': True,  # Distinguish manual captures from regular one-step captures.
        }
        self._handle_notification_data('demo', notification_data)

    def _send_void_request(self):
        """ Override of payment to simulate a void request.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_void_request()
        if self.provider_code != 'demo':
            return

        notification_data = {'reference': self.reference, 'simulated_state': 'cancel'}
        self._handle_notification_data('demo', notification_data)

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on dummy data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The dummy notification data
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'demo' or len(tx) == 1:
            return tx

        reference = notification_data.get('reference')
        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'demo')])
        if not tx:
            raise ValidationError(
                "Demo: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on dummy data.

        Note: self.ensure_one()

        :param dict notification_data: The dummy notification data
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'demo':
            return

        if self.tokenize:
            # The reasons why we immediately tokenize the transaction regardless of the state rather
            # than waiting for the payment method to be validated ('authorized' or 'done') like the
            # other payment providers do are:
            # - To save the simulated state and payment details on the token while we have them.
            # - To allow customers to create tokens whose transactions will always end up in the
            #   said simulated state.
            self._demo_tokenize_from_notification_data(notification_data)

        state = notification_data['simulated_state']
        if state == 'pending':
            self._set_pending()
        elif state == 'done':
            if self.capture_manually and not notification_data.get('manual_capture'):
                self._set_authorized()
            else:
                self._set_done()
                # Immediately post-process the transaction if it is a refund, as the post-processing
                # will not be triggered by a customer browsing the transaction from the portal.
                if self.operation == 'refund':
                    self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        elif state == 'cancel':
            self._set_canceled()
        else:  # Simulate an error state.
            self._set_error(_("You selected the following demo payment status: %s", state))

    def _demo_tokenize_from_notification_data(self, notification_data):
        """ Create a new token based on the notification data.

        Note: self.ensure_one()

        :param dict notification_data: The fake notification data to tokenize from.
        :return: None
        """
        self.ensure_one()

        state = notification_data['simulated_state']
        token = self.env['payment.token'].create({
            'provider_id': self.provider_id.id,
            'payment_details': notification_data['payment_details'],
            'partner_id': self.partner_id.id,
            'provider_ref': 'fake provider reference',
            'verified': True,
            'demo_simulated_state': state,
        })
        self.write({
            'token_id': token,
            'tokenize': False,
        })
        _logger.info(
            "Created token with id %s for partner with id %s.", token.id, self.partner_id.id
        )
