# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.urls import urljoin

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_toss_payments import const

_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    toss_payments_payment_secret = fields.Char(
        string="Toss Payments Payment Secret", groups='base.group_system'
    )

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        """Override of `payment` to ensure that Toss Payments' requirements for references are
        satisfied.

        Toss Payments' requirements for transaction are as follows:
        - References can only be made of alphanumeric characters and/or '-' and '_'.
          The prefix is generated with 'tx' as default. This prevents the prefix from being
          generated based on document names that may contain non-allowed characters
          (e.g., INV/2025/...).

        :param str provider_code: The code of the provider handling the transaction.
        :param str prefix: The custom prefix used to compute the full reference.
        :return: The unique reference for the transaction.
        :rtype: str
        """
        if provider_code == 'toss_payments':
            prefix = payment_utils.singularize_reference_prefix()
        return super()._compute_reference(provider_code, prefix=prefix, separator=separator, **kwargs)

    def _get_specific_processing_values(self, *args):
        """Override of `payment` to return Toss Payments-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :return: The provider-specific processing values
        :rtype: dict
        """
        if self.provider_code != 'toss_payments':
            return super()._get_specific_processing_values(*args)

        base_url = self.provider_id.get_base_url()
        return {
            'order_name': self.reference,
            'partner_name': self.partner_name or "",
            'partner_email': self.partner_email or "",
            'partner_phone': self.partner_phone,
            'success_url': urljoin(base_url, const.PAYMENT_SUCCESS_RETURN_ROUTE),
            'fail_url': urljoin(base_url, f"{const.PAYMENT_FAILURE_RETURN_ROUTE}?access_token={payment_utils.generate_access_token(self.reference)}"),
        }

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != 'toss_payments':
            return super()._extract_reference(provider_code, payment_data)

        return payment_data['orderId']

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount from the payment data."""
        if self.provider_code != 'toss_payments':
            return super()._extract_amount_data(payment_data)

        return {
            'amount': float(payment_data.get('totalAmount')),
            'currency_code': const.SUPPORTED_CURRENCY,
        }

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != 'toss_payments':
            return super()._apply_updates(payment_data)

        # Update the provider reference.
        self.provider_reference = payment_data['paymentKey']

        # Save the secret key used for verifying webhook events. See `_verify_signature`.
        self.toss_payments_payment_secret = payment_data.get('secret')

        # Update the payment state.
        status = payment_data.get('status')
        if status == const.PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif status == const.PAYMENT_STATUS_MAPPING['canceled']:
            self._set_canceled()
        elif status in ('CANCELED', 'PARTIAL_CANCELED') and self.state == 'done':
            # Refunds are not implemented but webhook notifications are still sent on manual
            # cancellation on the Toss Payments merchant dashboard.
            pass
        else:
            self._set_error(self.env._("Received data with invalid payment status: %s", status))
