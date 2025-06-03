# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug import urls

from odoo import models
from odoo.exceptions import ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_iyzico.const import PAYMENT_STATUS_MAPPING
from odoo.addons.payment_iyzico.controllers.main import IyzicoController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return Iyzico specific processing values.

         Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'iyzico':
            return res

        api_url = self._iyzico_checkoutform_initialize()

        # Extract the payment link URL and params and embed them in the redirect form.
        parsed_url = urls.url_parse(api_url)
        url_params = urls.url_decode(parsed_url.query)
        rendering_values = {
            'api_url': api_url,
            'url_params': url_params,  # Encore the params as inputs to preserve them.
        }
        return rendering_values

    def _iyzico_checkoutform_initialize(self):
        """" Intialize checkout form request and return Iyzico payment page url.

        :return: Payment page url.
        :rtype: str
        """
        payload = self._iyzico_prepare_checkoutform_initialize_payload()
        _logger.info(
            "Sending 'CF Initialize' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payload)
        )
        transaction_data = self.provider_id._iyzico_make_request(
            '/payment/iyzipos/checkoutform/initialize/auth/ecom',
            payload=payload,
        )
        _logger.info(
            "Response of 'CF Initialize' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(transaction_data)
        )

        # Temporary store token to fetch transaction in the callback
        self.provider_reference = transaction_data.get('token')

        return transaction_data.get('paymentPageUrl')

    def _iyzico_prepare_checkoutform_initialize_payload(self):
        """ Create payload for the checkoutform initialize request based on the transaction values.

        :return: The request payload.
        :rtype: dict
        """
        base_url = self.provider_id.get_base_url()
        first_name, last_name = payment_utils.split_partner_name(self.partner_name)
        return {
            'basketId': self.reference,
            # Dummy basket item as it is required in iyzico
            'basketItems': [{
                'id': 'Dummy ItemID',
                'price': self.amount,
                'name': 'Dummy Product',
                'category1': 'Dummy Category',
                'itemType': "VIRTUAL",
            }],
            'billingAddress': {
                'address': self.partner_address,
                'contactName': self.partner_name,
                'city': self.partner_city,
                'country': self.partner_country_id.name,
            },
            'buyer': {
                'id': self.id,
                'name': first_name,
                'surname': last_name,
                'identityNumber': f'{first_name}_{self.partner_id.id}',
                'email': self.partner_email,
                'registrationAddress': self.partner_address,
                'city': self.partner_city,
                'country': self.partner_country_id.name,
                'ip': self.id,
            },
            'callbackUrl': urls.url_join(base_url, IyzicoController._return_url),
            'conversationId': self.reference,
            'currency': self.currency_id.name,
            'locale': self.env.lang == 'tr_TR' and 'tr' or 'en',
            "paidPrice": self.amount,
            'price': self.amount,
        }

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on Iyzico data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If inconsistent data are received.
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'iyzico' or len(tx) == 1:
            return tx

        token = notification_data.get('token')
        if not token:
            raise ValidationError(
                "Iyzico: " + self.env._("Received data with missing token.")
            )

        tx = self.search([('provider_reference', '=', token), ('provider_code', '=', 'iyzico')])
        if not tx:
            raise ValidationError(
                "Iyzico: " + self.env._("No transaction found.")
            )

        return tx

    def _compare_notification_data(self, notification_data):
        """ Override of `payment` to compare the transaction based on APS data.

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        :raise ValidationError: If the transaction's amount and currency don't match the
            notification data.
        """
        if self.provider_code != 'iyzico':
            return super()._compare_notification_data(notification_data)

        amount = notification_data.get('price')
        currency_code = notification_data.get('currency')
        self._validate_amount_and_currency(amount, currency_code)

    def _process_notification_data(self, notification_data):
        """ Override of `payment' to process the transaction based on APS data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        :raise ValidationError: If inconsistent data are received.
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'iyzico':
            return

        # Update the provider reference.
        self.provider_reference = notification_data.get('paymentId')

        # Update the payment state.
        status = notification_data.get('paymentStatus')
        if status in PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif status in PAYMENT_STATUS_MAPPING['error']:
            self._set_error(self.env._(
                "An error occurred during processing of your payment (code %(code)s:"
                " %(explanation)s). Please try again.",
                code=status, explanation=notification_data.get('errorMessage'),
            ))
        else:
            _logger.warning(
                "Received data with invalid payment status (%s) for transaction with reference %s",
                status, self.reference
            )
            self._set_error("Iyzico: " + self.env._("Unknown status code: %s", status))
