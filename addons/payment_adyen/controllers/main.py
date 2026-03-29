# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import binascii
import hashlib
import hmac
import json
import logging
import pprint

from werkzeug import urls

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools.pycompat import to_text

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_adyen import utils as adyen_utils
from odoo.addons.payment_adyen.const import CURRENCY_DECIMALS

_logger = logging.getLogger(__name__)


class AdyenController(http.Controller):

    @http.route('/payment/adyen/acquirer_info', type='json', auth='public')
    def adyen_acquirer_info(self, acquirer_id):
        """ Return public information on the acquirer.

        :param int acquirer_id: The acquirer handling the transaction, as a `payment.acquirer` id
        :return: Public information on the acquirer, namely: the state and client key
        :rtype: str
        """
        acquirer_sudo = request.env['payment.acquirer'].sudo().browse(acquirer_id).exists()
        return {
            'state': acquirer_sudo.state,
            'client_key': acquirer_sudo.adyen_client_key,
        }

    @http.route('/payment/adyen/payment_methods', type='json', auth='public')
    def adyen_payment_methods(self, acquirer_id, amount=None, currency_id=None, partner_id=None):
        """ Query the available payment methods based on the transaction context.

        :param int acquirer_id: The acquirer handling the transaction, as a `payment.acquirer` id
        :param float amount: The transaction amount
        :param int currency_id: The transaction currency, as a `res.currency` id
        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :return: The JSON-formatted content of the response and formatted amount
        :rtype: dict
        """
        acquirer_sudo = request.env['payment.acquirer'].sudo().browse(acquirer_id)
        currency = request.env['res.currency'].browse(currency_id)
        currency_code = currency_id and currency.name
        converted_amount = amount and currency_code and payment_utils.to_minor_currency_units(
            amount, currency, CURRENCY_DECIMALS.get(currency_code)
        )
        partner_sudo = partner_id and request.env['res.partner'].sudo().browse(partner_id).exists()
        # The lang is taken from the context rather than from the partner because it is not required
        # to be logged in to make a payment, and because the lang is not always set on the partner.
        # Adyen only supports a limited set of languages but, instead of looking for the closest
        # match in https://docs.adyen.com/checkout/components-web/localization-components, we simply
        # provide the lang string as is (after adapting the format) and let Adyen find the best fit.
        lang_code = (request.context.get('lang') or 'en-US').replace('_', '-')
        shopper_reference = partner_sudo and f'ODOO_PARTNER_{partner_sudo.id}'
        amount_formatted = {
            'value': converted_amount,
            'currency': request.env['res.currency'].browse(currency_id).name,  # ISO 4217
        }
        data = {
            'merchantAccount': acquirer_sudo.adyen_merchant_account,
            'amount': amount_formatted,
            'countryCode': partner_sudo.country_id.code or None,  # ISO 3166-1 alpha-2 (e.g.: 'BE')
            'shopperLocale': lang_code,  # IETF language tag (e.g.: 'fr-BE')
            'shopperReference': shopper_reference,
            'channel': 'Web',
        }
        payment_methods_data = acquirer_sudo._adyen_make_request(
            url_field_name='adyen_checkout_api_url',
            endpoint='/paymentMethods',
            payload=data,
            method='POST'
        )
        _logger.info("paymentMethods request response:\n%s", pprint.pformat(payment_methods_data))
        return {'payment_methods_data': payment_methods_data, 'amount_formatted': amount_formatted}

    @http.route('/payment/adyen/payments', type='json', auth='public')
    def adyen_payments(
        self, acquirer_id, reference, converted_amount, currency_id, partner_id, payment_method,
        access_token, browser_info=None
    ):
        """ Make a payment request and process the feedback data.

        :param int acquirer_id: The acquirer handling the transaction, as a `payment.acquirer` id
        :param str reference: The reference of the transaction
        :param int converted_amount: The amount of the transaction in minor units of the currency
        :param int currency_id: The currency of the transaction, as a `res.currency` id
        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :param dict payment_method: The details of the payment method used for the transaction
        :param str access_token: The access token used to verify the provided values
        :param dict browser_info: The browser info to pass to Adyen
        :return: The JSON-formatted content of the response
        :rtype: dict
        """
        # Check that the transaction details have not been altered. This allows preventing users
        # from validating transactions by paying less than agreed upon.
        if not payment_utils.check_access_token(
            access_token, reference, converted_amount, currency_id, partner_id
        ):
            raise ValidationError("Adyen: " + _("Received tampered payment request data."))

        # Make the payment request to Adyen
        acquirer_sudo = request.env['payment.acquirer'].sudo().browse(acquirer_id).exists()
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)])
        data = {
            'merchantAccount': acquirer_sudo.adyen_merchant_account,
            'amount': {
                'value': converted_amount,
                'currency': request.env['res.currency'].browse(currency_id).name,  # ISO 4217
            },
            'reference': reference,
            'paymentMethod': payment_method,
            'shopperReference': acquirer_sudo._adyen_compute_shopper_reference(partner_id),
            'recurringProcessingModel': 'CardOnFile',  # Most susceptible to trigger a 3DS check
            'shopperIP': payment_utils.get_customer_ip_address(),
            'shopperInteraction': 'Ecommerce',
            'shopperEmail': tx_sudo.partner_email or "",
            'shopperName': adyen_utils.format_partner_name(tx_sudo.partner_name),
            'telephoneNumber': tx_sudo.partner_phone or "",
            'storePaymentMethod': tx_sudo.tokenize,  # True by default on Adyen side
            'additionalData': {
                'allow3DS2': True
            },
            'channel': 'web',  # Required to support 3DS
            'origin': acquirer_sudo.get_base_url(),  # Required to support 3DS
            'browserInfo': browser_info,  # Required to support 3DS
            'returnUrl': urls.url_join(
                acquirer_sudo.get_base_url(),
                # Include the reference in the return url to be able to match it after redirection.
                # The key 'merchantReference' is chosen on purpose to be the same as that returned
                # by the /payments endpoint of Adyen.
                f'/payment/adyen/return?merchantReference={reference}'
            ),
            **adyen_utils.include_partner_addresses(tx_sudo),
        }
        response_content = acquirer_sudo._adyen_make_request(
            url_field_name='adyen_checkout_api_url',
            endpoint='/payments',
            payload=data,
            method='POST'
        )

        # Handle the payment request response
        _logger.info("payment request response:\n%s", pprint.pformat(response_content))
        request.env['payment.transaction'].sudo()._handle_feedback_data(
            'adyen', dict(response_content, merchantReference=reference),  # Match the transaction
        )
        return response_content

    @http.route('/payment/adyen/payment_details', type='json', auth='public')
    def adyen_payment_details(self, acquirer_id, reference, payment_details):
        """ Submit the details of the additional actions and process the feedback data.

         The additional actions can have been performed both from the inline form or during a
         redirection.

        :param int acquirer_id: The acquirer handling the transaction, as a `payment.acquirer` id
        :param str reference: The reference of the transaction
        :param dict payment_details: The details of the additional actions performed for the payment
        :return: The JSON-formatted content of the response
        :rtype: dict
        """
        # Make the payment details request to Adyen
        acquirer_sudo = request.env['payment.acquirer'].browse(acquirer_id).sudo()
        response_content = acquirer_sudo._adyen_make_request(
            url_field_name='adyen_checkout_api_url',
            endpoint='/payments/details',
            payload=payment_details,
            method='POST'
        )

        # Handle the payment details request response
        _logger.info("payment details request response:\n%s", pprint.pformat(response_content))
        request.env['payment.transaction'].sudo()._handle_feedback_data(
            'adyen', dict(response_content, merchantReference=reference),  # Match the transaction
        )

        return response_content

    @http.route('/payment/adyen/return', type='http', auth='public', csrf=False, save_session=False)
    def adyen_return_from_redirect(self, **data):
        """ Process the data returned by Adyen after redirection.

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user if they are redirected to this route with a POST request. Indeed, as the session
        cookie is created without a `SameSite` attribute, some browsers that don't implement the
        recommended default `SameSite=Lax` behavior will not include the cookie in the redirection
        request from the payment provider to Odoo. As the redirection to the '/payment/status' page
        will satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.

        :param dict data: Feedback data. May include custom params sent to Adyen in the request to
                          allow matching the transaction when redirected here.
        """
        # Retrieve the transaction based on the reference included in the return url
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_feedback_data(
            'adyen', data
        )

        # Overwrite the operation to force the flow to 'redirect'. This is necessary because even
        # thought Adyen is implemented as a direct payment provider, it will redirect the user out
        # of Odoo in some cases. For instance, when a 3DS1 authentication is required, or for
        # special payment methods that are not handled by the drop-in (e.g. Sofort).
        tx_sudo.operation = 'online_redirect'

        # Query and process the result of the additional actions that have been performed
        _logger.info("handling redirection from Adyen with data:\n%s", pprint.pformat(data))
        self.adyen_payment_details(
            tx_sudo.acquirer_id.id,
            data['merchantReference'],
            {
                'details': {
                    'redirectResult': data['redirectResult'],
                },
            },
        )

        # Redirect the user to the status page
        return request.redirect('/payment/status')

    @http.route('/payment/adyen/notification', type='json', auth='public')
    def adyen_notification(self):
        """ Process the data sent by Adyen to the webhook based on the event code.

        See https://docs.adyen.com/development-resources/webhooks/understand-notifications for the
        exhaustive list of event codes.

        :return: The '[accepted]' string to acknowledge the notification
        :rtype: str
        """
        data = json.loads(request.httprequest.data)
        for notification_item in data['notificationItems']:
            notification_data = notification_item['NotificationRequestItem']

            # Check the source and integrity of the notification
            received_signature = notification_data.get('additionalData', {}).get('hmacSignature')
            PaymentTransaction = request.env['payment.transaction']
            try:
                acquirer_sudo = PaymentTransaction.sudo()._get_tx_from_feedback_data(
                    'adyen', notification_data
                ).acquirer_id  # Find the acquirer based on the transaction
            except ValidationError:
                # Warn rather than log the traceback to avoid noise when a POS payment notification
                # is received and the corresponding `payment.transaction` record is not found.
                _logger.warning("unable to find the transaction; skipping to acknowledge")
            else:
                if not self._verify_notification_signature(
                    received_signature, notification_data, acquirer_sudo.adyen_hmac_key
                ):
                    continue

                # Check whether the event of the notification succeeded and reshape the notification
                # data for parsing
                _logger.info("notification received:\n%s", pprint.pformat(notification_data))
                success = notification_data['success'] == 'true'
                event_code = notification_data['eventCode']
                if event_code == 'AUTHORISATION' and success:
                    notification_data['resultCode'] = 'Authorised'
                elif event_code == 'CANCELLATION' and success:
                    notification_data['resultCode'] = 'Cancelled'
                elif event_code == 'REFUND':
                    notification_data['resultCode'] = 'Authorised' if success else 'Error'
                else:
                    continue  # Don't handle unsupported event codes and failed events
                try:
                    # Handle the notification data as a regular feedback
                    PaymentTransaction.sudo()._handle_feedback_data('adyen', notification_data)
                except ValidationError:  # Acknowledge the notification to avoid getting spammed
                    _logger.exception(
                        "unable to handle the notification data;skipping to acknowledge"
                    )

        return '[accepted]'  # Acknowledge the notification

    def _verify_notification_signature(self, received_signature, payload, hmac_key):
        """ Check that the signature computed from the payload matches the received one.

        See https://docs.adyen.com/development-resources/webhooks/verify-hmac-signatures

        :param str received_signature: The signature sent with the notification
        :param dict payload: The notification payload
        :param str hmac_key: The HMAC key of the acquirer handling the transaction
        :return: Whether the signatures match
        :rtype: str
        """

        def _flatten_dict(_value, _path_base='', _separator='.'):
            """ Recursively generate a flat representation of a dict.

            :param Object _value: The value to flatten. A dict or an already flat value
            :param str _path_base: They base path for keys of _value, including preceding separators
            :param str _separator: The string to use as a separator in the key path
            """
            if isinstance(_value, dict):  # The inner value is a dict, flatten it
                _path_base = _path_base if not _path_base else _path_base + _separator
                for _key in _value:
                    yield from _flatten_dict(_value[_key], _path_base + str(_key))
            else:  # The inner value cannot be flattened, yield it
                yield _path_base, _value

        def _to_escaped_string(_value):
            """ Escape payload values that are using illegal symbols and cast them to string.

            String values containing `\\` or `:` are prefixed with `\\`.
            Empty values (`None`) are replaced by an empty string.

            :param Object _value: The value to escape
            :return: The escaped value
            :rtype: string
            """
            if isinstance(_value, str):
                return _value.replace('\\', '\\\\').replace(':', '\\:')
            elif _value is None:
                return ''
            else:
                return str(_value)

        if not received_signature:
            _logger.warning("ignored notification with missing signature")
            return False

        # Compute the signature from the payload
        signature_keys = [
            'pspReference', 'originalReference', 'merchantAccountCode', 'merchantReference',
            'amount.value', 'amount.currency', 'eventCode', 'success'
        ]
        # Flatten the payload to allow accessing inner dicts naively
        flattened_payload = {k: v for k, v in _flatten_dict(payload)}
        # Build the list of signature values as per the list of required signature keys
        signature_values = [flattened_payload.get(key) for key in signature_keys]
        # Escape values using forbidden symbols
        escaped_values = [_to_escaped_string(value) for value in signature_values]
        # Concatenate values together with ':' as delimiter
        signing_string = ':'.join(escaped_values)
        # Convert the HMAC key to the binary representation
        binary_hmac_key = binascii.a2b_hex(hmac_key.encode('ascii'))
        # Calculate the HMAC with the binary representation of the signing string with SHA-256
        binary_hmac = hmac.new(binary_hmac_key, signing_string.encode('utf-8'), hashlib.sha256)
        # Calculate the signature by encoding the result with Base64
        expected_signature = base64.b64encode(binary_hmac.digest())

        # Compare signatures
        if received_signature != to_text(expected_signature):
            _logger.warning("ignored event with invalid signature")
            return False

        return True
