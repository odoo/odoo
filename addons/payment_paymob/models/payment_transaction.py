# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug import urls

from odoo import _, api, models
from odoo.exceptions import ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_paymob.controllers.main import PaymobController


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        """ Override of `payment` to ensure that Paymob references are unique.

        :param str provider_code: The code of the provider handling the transaction.
        :param str prefix: The custom prefix used to compute the full reference.
        :param str separator: The custom separator used to separate the prefix from the suffix.
        :return: The unique reference for the transaction.
        :rtype: str
        """
        if provider_code == 'paymob':
            prefix = payment_utils.singularize_reference_prefix()

        return super()._compute_reference(
            provider_code, prefix=prefix, separator=separator, **kwargs
        )

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return Paymob-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The dict of provider-specific rendering values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'paymob':
            return res

        payload = self._paymob_prepare_payment_request_payload()
        _logger.info(
            "Sending '/v1/intention/' request for link creation:\n%s", pprint.pformat(payload)
        )
        payment_data = self.provider_id._paymob_make_request(
            '/v1/intention/', payload=payload, is_client_request=True
        )
        _logger.info(
            "Received response from '/v1/intention/' request:\n%s", pprint.pformat(payment_data)
        )
        # The provider reference is set to allow fetching the payment status after redirection.
        self.provider_reference = payment_data.get('id')
        paymob_client_secret = payment_data.get('client_secret')

        paymob_url = self.provider_id._paymob_get_api_url()
        api_url = f'{paymob_url}/unifiedcheckout/'
        url_params = {
            'publicKey': self.provider_id.paymob_public_key,
            'clientSecret': paymob_client_secret,
        }
        return {'api_url': api_url, 'url_params': url_params}

    def _paymob_prepare_payment_request_payload(self):
        """ Create the payload for the payment request based on the transaction values.

        :return: The request payload.
        :rtype: dict
        """
        partner_first_name, partner_last_name = payment_utils.split_partner_name(self.partner_name)
        payment_method_codes = [self.payment_method_code]

        # If the user selects the Oman Net Payment Method to pay, Integration ID for both Card and
        # Oman Net Integrations should be passed in the Intention API. The transaction will fail if
        # you only pass Oman Net Integration ID.
        if self.payment_method_code == 'omannet':
            payment_method_codes.append('card')

        # Suffix to all payment methods with the environment.
        environment = 'live' if self.provider_id.state == 'enabled' else 'test'
        payment_method_codes = [
            f'{code.replace("_", "")}{environment}' for code in payment_method_codes
        ]

        base_url = self.get_base_url()
        redirect_url = urls.url_join(base_url, PaymobController._return_url)
        webhook_url = urls.url_join(base_url, PaymobController._webhook_url)

        return {
            'special_reference': self.reference,
            'amount': payment_utils.to_minor_currency_units(self.amount, self.currency_id),
            'currency': self.currency_id.name,
            'payment_methods': payment_method_codes,
            'notification_url': webhook_url,
            'redirection_url': redirect_url,
            'billing_data': {
                'first_name': partner_first_name or partner_last_name or '',
                'last_name': partner_last_name or '',
                'email': self.partner_email or '',
                'street': self.partner_address or '',
                'state': self.partner_state_id.name or '',
                'phone_number': (self.partner_phone or '').replace(' ', ''),
                'country': self.partner_country_id.code or '',
            },
        }

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on Paymob data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: payment.transaction
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'paymob' or len(tx) == 1:
            return tx

        tx = self.search([
            ('reference', '=', notification_data.get('merchant_order_id')),
            ('provider_code', '=', 'paymob'),
        ])
        if not tx:
            raise ValidationError(_(
                "No transaction found matching reference %(ref)s.",
                ref=notification_data.get('merchant_order_id'),
            ))
        return tx

    def _compare_notification_data(self, notification_data):
        """ Override of `payment` to compare the transaction based on Paymob data.

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        :raise ValidationError: If the transaction's amount and currency don't match the
                                notification data.
        """
        if self.provider_code != 'paymob':
            return super()._compare_notification_data(notification_data)

        amount_cents = float(notification_data.get('amount_cents'))
        amount = payment_utils.to_major_currency_units(amount_cents, self.currency_id)
        currency_code = notification_data.get('currency')
        self._validate_amount_and_currency(amount, currency_code)

    def _process_notification_data(self, notification_data):
        """ Override of `payment` to process the transaction based on Paymob data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'paymob':
            return

        # Update the payment state.
        if notification_data.get('pending') == 'true':
            self._set_pending()
        elif notification_data.get('success') == 'true':
            self._set_done()
        else:
            _logger.info(
                "Received data with unsuccessful payment status for transaction with reference %s",
                self.reference
            )
            message = notification_data.get('data.message')
            self._set_error(_(
                "An error occurred during the processing of your payment (%(msg)s). Please try"
                " again.", msg=message
            ))
