# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round
from odoo.tools.urls import urljoin

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_xendit import const
from odoo.addons.payment_xendit.controllers.main import XenditController


_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return Xendit-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        if self.provider_code != 'xendit':
            return super()._get_specific_processing_values(processing_values)

        return {
            'rounded_amount': self._get_rounded_amount(),
        }

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return Xendit-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'xendit' or self.payment_method_code == 'card':
            return res

        # Initiate the payment and retrieve the invoice data.
        payload = self._xendit_prepare_invoice_request_payload()
        try:
            invoice_data = self._send_api_request('POST', 'v2/invoices', json=payload)
        except ValidationError as error:
            self._set_error(str(error))
            return {}

        # Extract the payment link URL and embed it in the redirect form.
        rendering_values = {
            'api_url': invoice_data.get('invoice_url')
        }
        return rendering_values

    def _xendit_prepare_invoice_request_payload(self):
        """ Create the payload for the invoice request based on the transaction values.

        :return: The request payload.
        :rtype: dict
        """
        base_url = self.provider_id.get_base_url()
        redirect_url = urljoin(base_url, XenditController._return_url)
        access_token = payment_utils.generate_access_token(self.reference, self.amount)
        success_url_params = urls.url_encode({
            'tx_ref': self.reference,
            'access_token': access_token,
            'success': 'true',
        })
        payload = {
            'external_id': self.reference,
            'amount': self._get_rounded_amount(),
            'description': self.reference,
            'customer': {
                'given_names': self.partner_name,
            },
            'success_redirect_url': f'{redirect_url}?{success_url_params}',
            'failure_redirect_url': redirect_url,
            'payment_methods': [const.PAYMENT_METHODS_MAPPING.get(
                self.payment_method_code, self.payment_method_code.upper())
            ],
            'currency': self.currency_id.name,
        }
        # If it's one of FPX methods, assign the payment methods as FPX automatically
        if self.payment_method_code == 'fpx':
            payload['payment_methods'] = const.FPX_METHODS
        # Extra payload values that must not be included if empty.
        if self.partner_email:
            payload['customer']['email'] = self.partner_email
        if phone := self.partner_id.phone:
            payload['customer']['mobile_number'] = phone
        address_details = {}
        if self.partner_city:
            address_details['city'] = self.partner_city
        if self.partner_country_id.name:
            address_details['country'] = self.partner_country_id.name
        if self.partner_zip:
            address_details['postal_code'] = self.partner_zip
        if self.partner_state_id.name:
            address_details['state'] = self.partner_state_id.name
        if self.partner_address:
            address_details['street_line1'] = self.partner_address
        if address_details:
            payload['customer']['addresses'] = [address_details]

        return payload

    def _send_payment_request(self):
        """Override of `payment` to send a payment request to Xendit."""
        if self.provider_code != 'xendit':
            return super()._send_payment_request()

        self._xendit_create_charge(self.token_id.provider_ref)

    def _xendit_create_charge(self, token_ref, auth_id=None):
        """ Create a charge on Xendit using the `credit_card_charges` endpoint.

        :param str token_ref: The reference of the Xendit token to use to make the payment.
        :param str auth_id: The authentication id to use to make the payment.
        :return: None
        """
        payload = {
            'token_id': token_ref,
            'external_id': self.reference,
            'amount': self._get_rounded_amount(),
            'currency': self.currency_id.name,
        }
        if auth_id:  # The payment goes through an authentication.
            payload['authentication_id'] = auth_id

        if self.token_id or self.tokenize:  # The tx uses a token or is tokenized.
            payload['is_recurring'] = True  # Ensure that next payments will not require 3DS.

        try:
            charge_payment_data = self._send_api_request(
                'POST', 'credit_card_charges', json=payload
            )
        except ValidationError as error:
            self._set_error(str(error))
        else:
            self._process('xendit', charge_payment_data)

    def _get_rounded_amount(self):
        decimal_places = const.CURRENCY_DECIMALS.get(
            self.currency_id.name, self.currency_id.decimal_places
        )
        return float_round(self.amount, decimal_places, rounding_method='DOWN')

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != 'xendit':
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get('external_id')

    def _extract_amount_data(self, payment_data):
        """Override of payment to extract the amount and currency from the payment data."""
        if self.provider_code != 'xendit':
            return super()._extract_amount_data(payment_data)

        amount = payment_data.get('amount') or payment_data.get('authorized_amount')
        currency_code = payment_data.get('currency')
        return {
            'amount': float(amount),
            'currency_code': currency_code,
            'precision_digits': const.CURRENCY_DECIMALS.get(currency_code),
        }

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != 'xendit':
            return super()._apply_updates(payment_data)

        # Update the provider reference.
        self.provider_reference = payment_data.get('id')

        # Update payment method.
        # If it's one of FPX Methods, assign the payment method as FPX automatically
        payment_method_code = payment_data.get('payment_method', '')
        if payment_method_code in const.FPX_METHODS:
            payment_method_code = 'fpx'

        payment_method = self.env['payment.method']._get_from_code(
            payment_method_code, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        payment_status = payment_data.get('status')
        if payment_status in const.PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['cancel']:
            self._set_canceled()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['error']:
            failure_reason = payment_data.get('failure_reason')
            self._set_error(_(
                "An error occurred during the processing of your payment (%s). Please try again.",
                failure_reason,
            ))

    def _extract_token_values(self, payment_data):
        """Override of `payment` to return token data based on Xendit data.

        Note: self.ensure_one() from :meth: `_tokenize`

        :param dict payment_data: The payment data sent by the provider.
        :return: Data to create a token.
        :rtype: dict
        """
        if self.provider_code != 'xendit':
            return super()._extract_token_values(payment_data)

        card_info = payment_data['masked_card_number'][-4:]  # Xendit pads details with X's.

        return {
            'payment_details': card_info,
            'provider_ref': payment_data['credit_card_token_id'],
        }
