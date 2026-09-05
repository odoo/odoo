# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import re
from uuid import uuid4

from werkzeug import urls

from odoo import _, models
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import float_round

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_xendit import const
from odoo.addons.payment_xendit.controllers.main import XenditController


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return Xendit-specific processing values.

        For a token payment that requires 3DS authentication, this also includes a redirect form
        to let the customer complete it.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'xendit':
            return res

        if self.currency_id.name in const.CURRENCY_DECIMALS:
            rounding = const.CURRENCY_DECIMALS.get(self.currency_id.name)
        else:
            rounding = self.currency_id.decimal_places
        rounded_amount = float_round(self.amount, rounding, rounding_method='DOWN')
        specific_values = {
            'rounded_amount': rounded_amount,
            'access_token': payment_utils.generate_access_token(self.reference),
            'currency': self.currency_id.name,
        }

        if self.operation == 'online_token':
            auth_url = self._xendit_get_pending_authentication_url()
            if auth_url:
                specific_values['pending_authentication_url'] = auth_url
        return specific_values

    def _xendit_get_pending_authentication_url(self):
        """ Return the URL to redirect the customer to for a token payment that requires 3DS
        authentication, as Xendit doesn't skip 3DS by default and can challenge card-on-file
        charges.

        :return: The redirect URL, or None if no additional action is required.
        :rtype: str | None
        """
        if self.state != 'pending' or not self.provider_reference:
            return None

        payment_request_data = self.provider_id._xendit_make_request(
            f'v3/payment_requests/{self.provider_reference}',
            api_version='2024-11-11',
            method='GET',
        )
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

        payload = self._xendit_prepare_session_request_payload()
        _logger.info("Sending session request for link creation:\n%s", pprint.pformat(payload))
        session_data = self.provider_id._xendit_make_request('sessions', payload=payload)
        _logger.info("Received session request response:\n%s", pprint.pformat(session_data))

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
            request_kwargs = {'api_version': '2024-11-11', 'method': 'GET'}
        else:
            endpoint = f'sessions/{self.provider_reference}'
            request_kwargs = {'method': 'GET'}

        try:
            data = self.provider_id._xendit_make_request(endpoint, **request_kwargs)
        except ValidationError:
            _logger.exception(
                "Unable to fetch the status of %s upon return; relying on the webhook.", endpoint
            )
            return
        _logger.info("Received status sync response:\n%s", pprint.pformat(data))
        self._handle_notification_data('xendit', data)

    def _xendit_get_return_url(self):
        """ Return the URL Xendit should redirect the customer to after a payment attempt.

        :return: The return URL.
        :rtype: str
        """
        return urls.url_join(self.provider_id.get_base_url(), XenditController._return_url)

    def _xendit_prepare_session_request_payload(self):
        """ Create the payload for the session request based on the transaction values.

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
        if phone := self.partner_id.mobile or self.partner_id.phone:
            payload['customer']['mobile_number'] = re.sub(r'[^\d+]', '', phone)
        if session_type == 'PAY' and self.tokenize and self.payment_method_code == 'card':
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
        :raise UserError: If the transaction is not linked to a token.
        """
        super()._send_payment_request()
        if self.provider_code != 'xendit':
            return

        if not self.token_id:
            raise ValidationError("Xendit: " + _("The transaction is not linked to a token."))

        payment_method_code = self.token_id.payment_method_id.code
        self._xendit_create_token_charge(self.token_id.provider_ref, payment_method_code)

    def _xendit_create_token_charge(self, token_ref, payment_method_code):
        """ Create a charge on Xendit using the `payment_requests` endpoint with a saved token.

        :param str token_ref: The Xendit payment token ID.
        :param str payment_method_code: The payment method code of the token.
        :return: None
        """
        if self.currency_id.name in const.CURRENCY_DECIMALS:
            rounding = const.CURRENCY_DECIMALS.get(self.currency_id.name)
        else:
            rounding = self.currency_id.decimal_places
        rounded_amount = float_round(self.amount, rounding, rounding_method='DOWN')

        payload = {
            'reference_id': self.reference,
            'type': 'PAY',
            'country': (self.partner_id.country_id or self.company_id.country_id).code,
            'currency': self.currency_id.name,
            'request_amount': rounded_amount,
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

        payment_request_data = self.provider_id._xendit_make_request(
            'v3/payment_requests', payload=payload, api_version='2024-11-11'
        )
        self._handle_notification_data('xendit', payment_request_data)

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on the notification data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: payment.transaction
        :raise ValidationError: If inconsistent data were received.
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'xendit' or len(tx) == 1:
            return tx

        reference = notification_data.get('reference_id')
        if not reference:
            raise ValidationError("Xendit: " + _("Received data with missing reference."))

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'xendit')])
        if not tx:
            # Xendit appends a random suffix to the reference of the payment request created from
            # the session, e.g. 'INV/2026/000062_GiWjPj9h9K'. Strip the suffix to find the
            # transaction matching the session reference.
            reference = reference.rsplit('_', 1)[0]
            tx = self.search([('reference', '=', reference), ('provider_code', '=', 'xendit')])
        if not tx:
            raise ValidationError(
                "Xendit: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of `payment` to process the transaction based on Xendit data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        :raise ValidationError: If inconsistent data were received.
        """
        self.ensure_one()

        super()._process_notification_data(notification_data)
        if self.provider_code != 'xendit':
            return

        self.provider_reference = notification_data.get(
            'payment_session_id'
        ) or notification_data.get('payment_request_id') or notification_data.get('id')

        # Update payment method.
        channel_code = notification_data.get('channel_code', '')
        if channel_code in const.FPX_METHODS:
            channel_code = 'fpx'
        payment_method_code = channel_code or notification_data.get('payment_method', '')

        payment_method = self.env['payment.method']._get_from_code(
            payment_method_code, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        payment_status = notification_data.get('status')
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
            if self.tokenize:
                self._xendit_tokenize_from_notification_data(notification_data)
            self._set_done()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['cancel']:
            self._set_canceled()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['error']:
            failure_reason = notification_data.get('failure_reason') or notification_data.get(
                'failure_code'
            )
            self._set_error(_(
                "An error occurred during the processing of your payment (%s). Please try again.",
                failure_reason,
            ))

    def _xendit_tokenize_from_notification_data(self, notification_data):
        """ Create a new token based on the notification data.

        The masked card number is not included in payment or payment request notifications, but
        is included in `payment_token.activation` webhook notifications. If it is missing, it is
        instead fetched from the payment token itself.

        :param dict notification_data: Xendit's response to a payment request API response, or a
            payment_session/payment_token webhook.
        :return: None
        """
        payment_token_id = notification_data.get('payment_token_id')
        if not payment_token_id:
            _logger.warning(
                "No payment_token_id found in notification data for transaction %s", self.reference
            )
            return

        card_details = notification_data.get('channel_properties', {}).get('card_details', {})
        if not card_details:
            token_data = self.provider_id._xendit_make_request(
                f'v3/payment_tokens/{payment_token_id}', api_version='2024-11-11', method='GET'
            )
            card_details = token_data.get('channel_properties', {}).get('card_details', {})
        masked_card = card_details.get('masked_card_number', '')
        card_info = masked_card[-4:] if masked_card else '****'

        token = self.env['payment.token'].create({
            "provider_id": self.provider_id.id,
            "payment_method_id": self.payment_method_id.id,
            "payment_details": card_info,
            "partner_id": self.partner_id.id,
            "provider_ref": payment_token_id,
        })
        self.write({
            'token_id': token.id,
            'tokenize': False,
        })
        _logger.info(
            "created token with id %(token_id)s for partner with id %(partner_id)s from "
            "transaction with reference %(ref)s",
            {
                'token_id': token.id,
                'partner_id': self.partner_id.id,
                'ref': self.reference,
            },
        )
