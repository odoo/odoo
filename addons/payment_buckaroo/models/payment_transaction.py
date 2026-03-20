# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.tools import urls

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_buckaroo import const
from odoo.addons.payment_buckaroo.controllers.main import BuckarooController


_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Buckaroo-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        if self.provider_code != 'buckaroo':
            return super()._get_specific_rendering_values(processing_values)

        return_url = urls.urljoin(self.provider_id.get_base_url(), BuckarooController._return_url)
        rendering_values = {
            'api_url': self.provider_id._buckaroo_get_api_url(),
            'Brq_websitekey': self.provider_id.buckaroo_website_key,
            'Brq_amount': self.amount,
            'Brq_currency': self.currency_id.name,
            'Brq_invoicenumber': self.reference,
            # Include all 4 URL keys despite they share the same value as they are part of the sig.
            'Brq_return': return_url,
            'Brq_returncancel': return_url,
            'Brq_returnerror': return_url,
            'Brq_returnreject': return_url,
        }
        if self.partner_lang:
            rendering_values['Brq_culture'] = self.partner_lang.replace('_', '-')
        rendering_values['Brq_signature'] = self.provider_id._buckaroo_generate_digital_sign(
            rendering_values, incoming=False
        )
        return rendering_values

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != 'buckaroo':
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get('brq_invoicenumber')

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != 'buckaroo':
            return super()._extract_amount_data(payment_data)

        amount = payment_data.get('brq_amount')
        currency_code = payment_data.get('brq_currency')
        return {
            'amount': float(amount),
            'currency_code': currency_code,
        }

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != 'buckaroo':
            return super()._apply_updates(payment_data)

        # Update the provider reference.
        transaction_keys = payment_data.get('brq_transactions')
        if not transaction_keys:
            self._set_error(_("Received data with missing transaction keys"))
            return
        # BRQ_TRANSACTIONS can hold multiple, comma-separated, tx keys. In practice, it holds only
        # one reference. So we split for semantic correctness and keep the first transaction key.
        self.provider_reference = transaction_keys.split(',')[0]

        # Update the payment method.
        payment_method_code = payment_data.get('brq_payment_method')
        payment_method = self.env['payment.method']._get_from_code(
            payment_method_code, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        status_code = int(payment_data.get('brq_statuscode') or 0)
        if status_code in const.STATUS_CODES_MAPPING['pending']:
            self._set_pending()
        elif status_code in const.STATUS_CODES_MAPPING['done']:
            self._set_done()
        elif status_code in const.STATUS_CODES_MAPPING['cancel']:
            self._set_canceled()
        elif status_code in const.STATUS_CODES_MAPPING['refused']:
            self._set_error(_("Your payment was refused (code %s). Please try again.", status_code))
        elif status_code in const.STATUS_CODES_MAPPING['error']:
            self._set_error(_(
                "An error occurred during processing of your payment (code %s). Please try again.",
                status_code,
            ))
        else:
            _logger.warning(
                "Received data with invalid payment status (%s) for transaction %s.",
                status_code, self.reference
            )
            self._set_error(_("Unknown status code: %s.", status_code))
