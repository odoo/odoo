# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError


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

        payment_data = {'reference': self.reference, 'simulated_state': 'done'}
        self._process('demo', payment_data)

    def action_demo_set_canceled(self):
        """ Set the state of the demo transaction to 'cancel'.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.provider_code != 'demo':
            return

        payment_data = {'reference': self.reference, 'simulated_state': 'cancel'}
        self._process('demo', payment_data)

    def action_demo_set_error(self):
        """ Set the state of the demo transaction to 'error'.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.provider_code != 'demo':
            return

        payment_data = {'reference': self.reference, 'simulated_state': 'error'}
        self._process('demo', payment_data)

    # === BUSINESS METHODS === #

    def _send_payment_request(self):
        """Override of `payment` to simulate a payment request."""
        if self.provider_code != 'demo':
            return super()._send_payment_request()

        simulated_state = self.token_id.demo_simulated_state
        payment_data = {'reference': self.reference, 'simulated_state': simulated_state}
        self._process('demo', payment_data)

    def _send_capture_request(self):
        """Override of `payment` to simulate a capture request."""
        if self.provider_code != 'demo':
            return super()._send_capture_request()

        payment_data = {
            'reference': self.reference,
            'simulated_state': 'done',
            'manual_capture': True,  # Distinguish manual captures from regular one-step captures.
        }
        self._process('demo', payment_data)

    def _send_void_request(self):
        """Override of `payment` to simulate a void request."""
        if self.provider_code != 'demo':
            return super()._send_void_request()

        payment_data = {'reference': self.reference, 'simulated_state': 'cancel'}
        self._process('demo', payment_data)

    def _send_refund_request(self):
        """Override of `payment` to simulate a refund."""
        if self.provider_code != 'demo':
            return super()._send_refund_request()

        payment_data = {'reference': self.reference, 'simulated_state': 'done'}
        self._process('demo', payment_data)

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to skip the amount validation for demo flows."""
        if self.provider_code != 'demo':
            return super()._extract_amount_data(payment_data)
        return None

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != 'demo':
            return super()._apply_updates(payment_data)

        # Update the provider reference.
        self.provider_reference = f'demo-{self.reference}'

        # Create the token.
        if self.tokenize:
            # The reasons why we immediately tokenize the transaction instead of in `payment` are:
            # - To save the simulated state and payment details on the token while we have them.
            # - To allow customers to create tokens whose transactions will always end up in the
            #   said simulated state.
            self._tokenize(payment_data)

        # Update the payment state.
        state = payment_data['simulated_state']
        if state == 'pending':
            self._set_pending()
        elif state == 'done':
            if self.capture_manually and not payment_data.get('manual_capture'):
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

    def _extract_token_values(self, payment_data):
        """Override of `payment` to extract the token values from the payment data."""
        if self.provider_code != 'demo':
            return super()._extract_token_values(payment_data)

        # Do not tokenize the transaction twice as `_update_from_payment_data` already does.
        if self.state in ('done', 'authorized'):
            return {}

        state = payment_data['simulated_state']
        return {
            'payment_details': payment_data['payment_details'],
            'provider_ref': 'fake provider reference',
            'demo_simulated_state': state,
        }
