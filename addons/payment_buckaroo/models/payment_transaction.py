# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from werkzeug import urls

from odoo import _, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_buckaroo import const
from odoo.addons.payment_buckaroo.controllers.main import BuckarooController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Buckaroo-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'buckaroo':
            return res

        return_url = urls.url_join(self.provider_id.get_base_url(), BuckarooController._return_url)
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

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on Buckaroo data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The normalized notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'buckaroo' or len(tx) == 1:
            return tx

        reference = notification_data.get('brq_invoicenumber')
        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'buckaroo')])
        if not tx:
            raise ValidationError(
                "Buckaroo: " + _("No transaction found matching reference %s.", reference)
            )

        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Buckaroo data.

        Note: self.ensure_one()

        :param dict notification_data: The normalized notification data sent by the provider
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'buckaroo':
            return

        # Update the provider reference.
        transaction_keys = notification_data.get('brq_transactions')
        if not transaction_keys:
            raise ValidationError("Buckaroo: " + _("Received data with missing transaction keys"))
        # BRQ_TRANSACTIONS can hold multiple, comma-separated, tx keys. In practice, it holds only
        # one reference. So we split for semantic correctness and keep the first transaction key.
        self.provider_reference = transaction_keys.split(',')[0]

        # Update the payment method.
        payment_method_code = notification_data.get('brq_payment_method')
        payment_method = self.env['payment.method']._get_from_code(
            payment_method_code, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        status_code = int(notification_data.get('brq_statuscode') or 0)
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
                "received data with invalid payment status (%s) for transaction with reference %s",
                status_code, self.reference
            )
            self._set_error("Buckaroo: " + _("Unknown status code: %s", status_code))
