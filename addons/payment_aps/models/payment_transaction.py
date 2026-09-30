# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.tools import urls

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_aps import utils as aps_utils
from odoo.addons.payment_aps.const import PAYMENT_STATUS_MAPPING
from odoo.addons.payment_aps.controllers.main import APSController


_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        """ Override of `payment` to ensure that APS' requirements for references are satisfied.

        APS' requirements for transaction are as follows:
        - References can only be made of alphanumeric characters and/or '-' and '_'.
          The prefix is generated with 'tx' as default. This prevents the prefix from being
          generated based on document names that may contain non-allowed characters
          (eg: INV/2020/...).

        :param str provider_code: The code of the provider handling the transaction.
        :param str prefix: The custom prefix used to compute the full reference.
        :param str separator: The custom separator used to separate the prefix from the suffix.
        :return: The unique reference for the transaction.
        :rtype: str
        """
        if provider_code == 'aps':
            prefix = payment_utils.singularize_reference_prefix()

        return super()._compute_reference(provider_code, prefix=prefix, separator=separator, **kwargs)

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return APS-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction.
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        if self.provider_code != 'aps':
            return super()._get_specific_rendering_values(processing_values)

        converted_amount = payment_utils.to_minor_currency_units(self.amount, self.currency_id)
        base_url = self.provider_id.get_base_url()
        payment_option = aps_utils.get_payment_option(self.payment_method_id.code)
        rendering_values = {
            'command': 'PURCHASE',
            'access_code': self.provider_id.aps_access_code,
            'merchant_identifier': self.provider_id.aps_merchant_identifier,
            'merchant_reference': self.reference,
            'amount': str(converted_amount),
            'currency': self.currency_id.name,
            'language': self.partner_lang[:2],
            'customer_email': self.partner_id.email_normalized,
            'return_url': urls.urljoin(base_url, APSController._return_url),
        }
        if payment_option:  # Not included if the payment method is 'card'.
            rendering_values['payment_option'] = payment_option
        rendering_values.update({
            'signature': self.provider_id._aps_calculate_signature(
                rendering_values, incoming=False
            ),
            'api_url': self.provider_id._aps_get_api_url(),
        })
        return rendering_values

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the APS data."""
        if provider_code != 'aps':
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get('merchant_reference')

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != 'aps':
            return super()._extract_amount_data(payment_data)

        amount = payment_utils.to_major_currency_units(
            float(payment_data.get('amount', 0)), self.currency_id
        )
        return {
            'amount': amount,
            'currency_code': payment_data.get('currency'),
        }

    def _apply_updates(self, payment_data):
        """Override of `payment' to update the transaction based on the payment data."""
        if self.provider_code != 'aps':
            return super()._apply_updates(payment_data)

        # Update the provider reference.
        self.provider_reference = payment_data.get('fort_id')

        # Update the payment method.
        payment_option = payment_data.get('payment_option', '')
        payment_method = self.env['payment.method']._get_from_code(payment_option.lower())
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        status = payment_data.get('status')
        if not status:
            self._set_error(_("Received data with missing payment state."))
        elif status in PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif status in PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        else:  # Classify unsupported payment state as `error` tx state.
            status_description = payment_data.get('response_message')
            _logger.info(
                "Received data with invalid payment status (%(status)s) and reason '%(reason)s' "
                "for transaction %(ref)s.",
                {'status': status, 'reason': status_description, 'ref': self.reference},
            )
            self._set_error(_(
                "Received invalid transaction status %(status)s and reason '%(reason)s'.",
                status=status, reason=status_description
            ))
