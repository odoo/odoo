# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from uuid import uuid4

from werkzeug import urls

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.http import request
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

        For a token payment that requires 3DS authentication, this includes the authentication URL
        to let the customer complete it.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'xendit':
            return res

        if self.operation == 'online_token':
            auth_url = self._xendit_get_pending_authentication_url()
            if auth_url:
                res['pending_authentication_url'] = auth_url
        return res

    def _xendit_get_pending_authentication_url(self):
        """ Return the URL to redirect the customer to for a token payment that requires 3DS
        authentication, as Xendit doesn't skip 3DS by default and can challenge card-on-file
        charges.

        :return: The redirect URL, or None if no additional action is required.
        :rtype: str | None
        """
        if (
            self.state != 'pending'
            or not self.provider_reference
            or not self.token_id
            # A legacy (v2) token charge has no `v3/payment_requests` counterpart to look up.
            or not self.token_id.provider_ref.startswith(const.V3_TOKEN_ID_PREFIX)
        ):
            return None

        try:
            payment_request_data = self._send_api_request(
                'GET', f'v3/payment_requests/{self.provider_reference}', api_version='2024-11-11',
            )
        except ValidationError:
            # The charge itself already succeeded (synchronously) before this point; don't crash
            # the checkout confirmation over a failure to fetch the 3DS redirect that follows it.
            _logger.exception(
                "Unable to fetch the pending authentication URL for %s.", self.reference
            )
            return None
        if payment_request_data.get('status') != 'REQUIRES_ACTION':
            return None

        for action in payment_request_data.get('actions', []):
            if action.get('type') == 'REDIRECT_CUSTOMER':
                return action.get('value')
        return None

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return Xendit-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'xendit':
            return res

        payload = self._xendit_prepare_invoice_request_payload()
        try:
            session_data = self._send_api_request('POST', 'sessions', json=payload)
        except ValidationError as error:
            self._set_error(str(error))
            return {}

        # Save the session id now rather than waiting for the webhook, so that a customer
        # returning from checkout before the webhook arrives can still be checked against it.
        self.provider_reference = session_data.get('payment_session_id') or session_data.get('id')

        rendering_values = {
            'api_url': session_data.get('payment_link_url')
        }
        return rendering_values

    def _xendit_sync_from_provider(self):
        """ Fetch the current status of the transaction from Xendit and process it.

        Used as a fallback to the webhook when the customer returns from Xendit (either the
        hosted checkout page, or a 3DS authentication challenge for a token payment), in case the
        notification hasn't been received yet (e.g. delayed or dropped).

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if not self.provider_reference:
            return

        if self.operation == 'online_token':
            endpoint = f'v3/payment_requests/{self.provider_reference}'
            request_kwargs = {'api_version': '2024-11-11'}
        else:
            endpoint = f'sessions/{self.provider_reference}'
            request_kwargs = {}

        try:
            data = self._send_api_request('GET', endpoint, **request_kwargs)
        except ValidationError:
            _logger.exception(
                "Unable to fetch the status of %s upon return; relying on the webhook.", endpoint
            )
            return
        self._process('xendit', data)

    def _xendit_get_return_url(self):
        """ Return the URL Xendit should redirect the customer to after a payment attempt.

        :return: The return URL.
        :rtype: str
        """
        return urljoin(self.provider_id.get_base_url(), XenditController._return_url)

    def _xendit_prepare_invoice_request_payload(self):
        """ Create the payload for the session request based on the transaction values.

        The method name is kept from the legacy (v2) invoices API for backward compatibility; the
        payload is now built for the Payment Sessions API.

        :return: The request payload.
        :rtype: dict
        """
        redirect_url = self._xendit_get_return_url()
        access_token = payment_utils.generate_access_token(self.reference, self.amount)
        success_url_params = urls.url_encode({
            'tx_ref': self.reference,
            'access_token': access_token,
            'success': 'true',
        })
        partner_first_name, partner_last_name = payment_utils.split_partner_name(self.partner_name)

        if self.operation == 'validation':
            session_type = 'SAVE'
            amount = 0
        else:
            session_type = 'PAY'
            amount = self.amount

        payload = {
            'reference_id': self.reference,
            'session_type': session_type,
            'mode': 'PAYMENT_LINK',
            'amount': amount,
            'description': self.reference,
            'customer': {
                'reference_id': f'customer{self.partner_id.id}{uuid4().hex[:8]}',
                'type': 'INDIVIDUAL',
                'individual_detail': {
                    'given_names': re.sub(r'[^a-zA-Z0-9]', '', partner_first_name),
                    'surname': re.sub(r'[^a-zA-Z0-9]', '', partner_last_name),
                },
            },
            'success_return_url': f'{redirect_url}?{success_url_params}',
            'cancel_return_url': redirect_url,
            'allowed_payment_channels': [const.PAYMENT_METHODS_MAPPING.get(
                self.payment_method_code, self.payment_method_code.upper())
            ],
            'currency': self.currency_id.name,
        }
        if self.partner_id.country_id:
            payload['country'] = self.partner_id.country_id.code
        elif self.company_id.country_code:
            payload['country'] = self.company_id.country_code
        if self.payment_method_code == 'fpx':
            payload['allowed_payment_channels'] = const.FPX_METHODS
        if self.partner_email:
            payload['customer']['email'] = self.partner_email
        if phone := self.partner_id.phone:
            payload['customer']['mobile_number'] = re.sub(r'[^\d+]', '', phone)
        if self.operation != 'validation' and self.tokenize and self.payment_method_code == 'card':
            payload['allow_save_payment_method'] = 'FORCED'
            payload['channel_properties'] = {
                'cards': {
                    'card_on_file_type': 'CUSTOMER_UNSCHEDULED',
                }
            }
        return payload

    def _send_payment_request(self):
        """ Override of `payment` to send a payment request to Xendit.

        Note: self.ensure_one()

        :return: None
        :raise ValidationError: If the transaction is not linked to a token.
        """
        if self.provider_code != 'xendit':
            return super()._send_payment_request()

        if not self.token_id:
            raise ValidationError(_("The transaction is not linked to a token."))

        self._xendit_create_charge(self.token_id.provider_ref)

    def _xendit_create_charge(self, token_ref, auth_id=None):
        """ Create a charge on Xendit with the given token.

        Tokens created through the v3 Payment Tokens API are charged through the
        `v3/payment_requests` endpoint, and tokens saved before the migration to that API through
        the legacy (v2) `credit_card_charges` endpoint.

        :param str token_ref: The reference of the Xendit token to use to make the payment.
        :param str auth_id: Unused; kept for backward compatibility with the removed inline form.
        :return: None
        """
        try:
            if token_ref.startswith(const.V3_TOKEN_ID_PREFIX):
                payment_method_code = self.token_id.payment_method_id.code
                self._xendit_create_token_charge(token_ref, payment_method_code)
            else:
                self._xendit_create_legacy_token_charge(token_ref)
        except ValidationError as error:
            self._set_error(str(error))

    def _xendit_create_token_charge(self, token_ref, payment_method_code):
        """ Create a charge on Xendit using the `payment_requests` endpoint with a saved token.

        :param str token_ref: The Xendit payment token ID.
        :param str payment_method_code: The payment method code of the token.
        :return: None
        """
        payload = {
            'reference_id': self.reference,
            'type': 'PAY',
            'country': (self.partner_id.country_id or self.company_id.country_id).code,
            'currency': self.currency_id.name,
            'request_amount': self._get_rounded_amount(),
            'capture_method': 'AUTOMATIC',
            'payment_token_id': token_ref,
        }

        if payment_method_code == 'card':
            # Only used if the card unexpectedly requires a 3DS challenge; the transaction state
            # is otherwise updated by the webhook regardless of whether this URL is ever visited.
            return_url = self._xendit_get_return_url()
            success_return_url = return_url
            if request:
                # Let the customer be checked against Xendit on return, as a fallback in case the
                # webhook is delayed or dropped. Not available from a cron context (e.g. an
                # off-session subscription renewal), which never reaches this redirect anyway
                # since there is no cardholder to send through it.
                access_token = payment_utils.generate_access_token(self.reference, self.amount)
                success_url_params = urls.url_encode({
                    'tx_ref': self.reference,
                    'access_token': access_token,
                    'success': 'true',
                })
                success_return_url = f'{return_url}?{success_url_params}'
            # Offline charges (e.g. subscription renewals, backend payments by token) have no
            # cardholder present; flag them as merchant- rather than customer-initiated to reduce
            # the odds of a 3DS challenge.
            if self.operation == 'offline':
                card_on_file_type = 'MERCHANT_UNSCHEDULED'
            else:
                card_on_file_type = 'CUSTOMER_UNSCHEDULED'
            payload['channel_properties'] = {
                'card_on_file_type': card_on_file_type,
                'success_return_url': success_return_url,
                'failure_return_url': return_url,
            }

        payment_request_data = self._send_api_request(
            'POST', 'v3/payment_requests', json=payload, api_version='2024-11-11'
        )
        self._process('xendit', payment_request_data)

    def _xendit_create_legacy_token_charge(self, token_ref):
        """ Create a charge on Xendit using the legacy (v2) `credit_card_charges` endpoint, for
        tokens saved before the migration to the v3 Payment Tokens API.

        :param str token_ref: The Xendit v2 credit card token id.
        :return: None
        """
        payload = {
            'token_id': token_ref,
            'external_id': self.reference,
            'amount': self._get_rounded_amount(),
            'currency': self.currency_id.name,
            'is_recurring': True,  # Ensure that next payments will not require 3DS.
        }

        charge_payment_data = self._send_api_request('POST', 'credit_card_charges', json=payload)
        self._process('xendit', charge_payment_data)

    def _get_rounded_amount(self):
        decimal_places = const.CURRENCY_DECIMALS.get(
            self.currency_id.name, self.currency_id.decimal_places
        )
        return float_round(self.amount, decimal_places, rounding_method='DOWN')

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """ Override of `payment` to extract the reference from the payment data.

        `reference_id` is used by the sessions/v3 APIs; `external_id` is the legacy (v2)
        equivalent, still sent by `credit_card_charges` notifications.
        """
        if provider_code != 'xendit':
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get('reference_id') or payment_data.get('external_id')

    @api.model
    def _search_by_reference(self, provider_code, payment_data):
        """ Override of `payment` to fall back to a suffix-stripped reference.

        Xendit appends a random suffix to the reference of the payment request created from a
        session, e.g. 'INV/2026/000062_GiWjPj9h9K'. Strip the suffix and retry when the exact
        reference matches no transaction.

        :param str provider_code: The code of the provider handling the transaction.
        :param dict payment_data: The payment data sent by the provider.
        :return: The transaction, if found.
        :rtype: payment.transaction
        """
        tx = super()._search_by_reference(provider_code, payment_data)
        if provider_code != 'xendit' or tx:
            return tx

        reference = self._extract_reference(provider_code, payment_data)
        if not reference:
            return tx

        reference = reference.rsplit('_', 1)[0]
        return self.search([('reference', '=', reference), ('provider_code', '=', provider_code)])

    def _extract_amount_data(self, payment_data):
        """ Override of payment to extract the amount and currency from the payment data. """
        if self.provider_code != 'xendit':
            return super()._extract_amount_data(payment_data)

        amount = (
            payment_data.get('amount')
            or payment_data.get('authorized_amount')
            or payment_data.get('request_amount')
        )
        currency_code = payment_data.get('currency')
        return {
            'amount': float(amount),
            'currency_code': currency_code,
            'precision_digits': const.CURRENCY_DECIMALS.get(currency_code),
        }

    def _apply_updates(self, payment_data):
        """ Override of `payment` to update the transaction based on the payment data. """
        if self.provider_code != 'xendit':
            return super()._apply_updates(payment_data)

        self.provider_reference = payment_data.get(
            'payment_session_id'
        ) or payment_data.get('payment_request_id') or payment_data.get('id')

        # Update payment method.
        channel_code = payment_data.get('channel_code', '')
        if channel_code in const.FPX_METHODS:
            channel_code = 'fpx'
        payment_method_code = channel_code or payment_data.get('payment_method', '')

        payment_method = self.env['payment.method']._get_from_code(
            payment_method_code, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        payment_status = payment_data.get('status')
        if payment_status == 'REQUIRES_ACTION' and self.operation == 'offline':
            # There is no cardholder to redirect for an unattended charge (e.g. a subscription
            # renewal); fail instead of leaving the transaction stuck pending indefinitely.
            self._set_error(_(
                "The payment requires authentication from the customer, which isn't possible "
                "for this unattended transaction. Please ask the customer to pay manually."
            ))
        elif payment_status in const.PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['cancel']:
            self._set_canceled()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['error']:
            failure_reason = payment_data.get('failure_reason') or payment_data.get(
                'failure_code'
            )
            self._set_error(_(
                "An error occurred during the processing of your payment (%s). Please try again.",
                failure_reason,
            ))

    def _extract_token_values(self, payment_data):
        """ Override of `payment` to return token data based on Xendit data.

        The masked card number is not included in payment session or payment request data, but
        is included in `payment_token.activation` webhook notifications. If it is missing, it is
        instead fetched from the payment token itself.

        Note: self.ensure_one() from :meth: `_tokenize`

        :param dict payment_data: The payment data sent by the provider.
        :return: Data to create a token.
        :rtype: dict
        """
        if self.provider_code != 'xendit':
            return super()._extract_token_values(payment_data)

        payment_token_id = payment_data.get('payment_token_id')
        if not payment_token_id:
            _logger.warning(
                "No payment_token_id found in payment data for transaction %s", self.reference
            )
            return {}

        card_details = payment_data.get('channel_properties', {}).get('card_details', {})
        if not card_details:
            try:
                token_data = self._send_api_request(
                    'GET', f'v3/payment_tokens/{payment_token_id}', api_version='2024-11-11'
                )
            except ValidationError:
                # The payment itself already succeeded; don't fail the whole notification (and,
                # from the webhook, crash the request that must acknowledge it) over a failure to
                # fetch the masked card number for tokenization.
                _logger.exception(
                    "Unable to fetch payment token %s for transaction %s.",
                    payment_token_id, self.reference,
                )
                return {}
            card_details = token_data.get('channel_properties', {}).get('card_details', {})
        masked_card = card_details.get('masked_card_number', '')

        return {
            'payment_details': masked_card[-4:] if masked_card else '****',
            'provider_ref': payment_token_id,
        }
