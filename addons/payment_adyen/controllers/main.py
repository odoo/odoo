# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import binascii
import hashlib
import hmac
import pprint

from werkzeug.exceptions import Forbidden

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import py_to_js_locale, urls

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_adyen import utils as adyen_utils


_logger = get_payment_logger(__name__)


class AdyenController(http.Controller):

    _webhook_url = '/payment/adyen/notification'

    @http.route('/payment/adyen/payment_methods', type='jsonrpc', auth='public')
    def adyen_payment_methods(self, provider_id, formatted_amount=None, partner_id=None):
        """ Query the available payment methods based on the payment context.

        :param int provider_id: The provider handling the transaction, as a `payment.provider` id
        :param dict formatted_amount: The Adyen-formatted amount.
        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :return: The JSON-formatted content of the response
        :rtype: dict
        """
        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id)
        partner_sudo = partner_id and request.env['res.partner'].sudo().browse(partner_id).exists()
        # The lang is taken from the context rather than from the partner because it is not required
        # to be logged in to make a payment, and because the lang is not always set on the partner.
        # Adyen only supports a limited set of languages but, instead of looking for the closest
        # match in https://docs.adyen.com/checkout/components-web/localization-components, we simply
        # provide the lang string as is (after adapting the format) and let Adyen find the best fit.
        lang_code = py_to_js_locale(request.env.context.get('lang')) or 'en-US'
        shopper_reference = partner_sudo and f'ODOO_PARTNER_{partner_sudo.id}'
        partner_country_code = (
            partner_sudo.country_id.code or provider_sudo.company_id.country_id.code or 'NL'
        )
        data = {
            'merchantAccount': provider_sudo.adyen_merchant_account,
            'amount': formatted_amount,
            'countryCode': partner_country_code,  # ISO 3166-1 alpha-2 (e.g.: 'BE')
            'shopperLocale': lang_code,  # IETF BCP 47 language tag (e.g.: 'fr-BE')
            'shopperReference': shopper_reference,
            'channel': 'Web',
        }
        response_content = provider_sudo._send_api_request('POST', '/paymentMethods', json=data)
        response_content['country_code'] = partner_country_code
        return response_content

    @http.route('/payment/adyen/payments', type='jsonrpc', auth='public')
    def adyen_payments(
        self, provider_id, reference, converted_amount, currency_id, partner_id, payment_method,
        access_token, browser_info=None
    ):
        """Make a payment request and process the payment data.

        :param int provider_id: The provider handling the transaction, as a `payment.provider` id
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
            raise ValidationError(_("Received tampered payment request data."))

        # Prepare the payment request to Adyen
        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id).exists()
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)])
        partner_country_code = (
            tx_sudo.partner_country_id.code or provider_sudo.company_id.country_id.code or 'NL'
        )
        data = {
            'merchantAccount': provider_sudo.adyen_merchant_account,
            'amount': {
                'value': converted_amount,
                'currency': request.env['res.currency'].browse(currency_id).name,  # ISO 4217
            },
            'countryCode': partner_country_code,  # ISO 3166-1 alpha-2 (e.g.: 'BE')
            'reference': reference,
            'paymentMethod': payment_method,
            'shopperReference': provider_sudo._adyen_compute_shopper_reference(partner_id),
            'recurringProcessingModel': 'CardOnFile',  # Most susceptible to trigger a 3DS check
            'shopperIP': payment_utils.get_customer_ip_address(),
            'shopperInteraction': 'Ecommerce',
            'shopperEmail': tx_sudo.partner_email or "",
            'shopperName': adyen_utils.format_partner_name(tx_sudo.partner_name),
            'telephoneNumber': tx_sudo.partner_phone or "",
            'storePaymentMethod': tx_sudo.tokenize,  # True by default on Adyen side
            'authenticationData': {
                'threeDSRequestData': {
                    'nativeThreeDS': 'preferred',
                }
            },
            'channel': 'web',  # Required to support 3DS
            'origin': provider_sudo.get_base_url(),  # Required to support 3DS
            'browserInfo': browser_info,  # Required to support 3DS
            'returnUrl': urls.urljoin(
                provider_sudo.get_base_url(),
                # Include the reference in the return url to be able to match it after redirection.
                # The key 'merchantReference' is chosen on purpose to be the same as that returned
                # by the /payments endpoint of Adyen.
                f'/payment/adyen/return?merchantReference={reference}',
            ),
            **adyen_utils.include_partner_addresses(tx_sudo),
            'lineItems': [{
                'amountIncludingTax': converted_amount,
                'quantity': '1',
                'description': reference,
            }],
        }

        # Force the capture delay on Adyen side if the provider is not configured for capturing
        # payments manually. This is necessary because it's not possible to distinguish
        # 'AUTHORISATION' events sent by Adyen with the merchant account's capture delay set to
        # 'manual' from events with the capture delay set to 'immediate' or a number of hours. If
        # the merchant account is configured to capture payments with a delay but the provider is
        # not, we force the immediate capture to avoid considering authorized transactions as
        # captured on Odoo.
        if not provider_sudo.capture_manually:
            data.update(captureDelayHours=0)

        # Send the payment request to Adyen.
        idempotency_key = payment_utils.generate_idempotency_key(
            tx_sudo, scope='payment_request_controller'
        )

        response_content = provider_sudo._send_api_request(
            'POST', '/payments', json=data, idempotency_key=idempotency_key
        )
        tx_sudo._process(
            'adyen', dict(response_content, merchantReference=reference),  # Match the transaction
        )
        return response_content

    @http.route('/payment/adyen/payments/details', type='jsonrpc', auth='public')
    def adyen_payment_details(self, provider_id, reference, payment_details):
        """Submit the details of the additional actions and process the payment data.

         The additional actions can have been performed both from the inline form or during a
         redirection.

        :param int provider_id: The provider handling the transaction, as a `payment.provider` id
        :param str reference: The reference of the transaction
        :param dict payment_details: The details of the additional actions performed for the payment
        :return: The JSON-formatted content of the response
        :rtype: dict
        """
        # Make the payment details request to Adyen
        provider_sudo = request.env['payment.provider'].browse(provider_id).sudo()
        response_content = provider_sudo._send_api_request(
            'POST', '/payments/details', json=payment_details
        )

        # Process the payment data request response.
        request.env['payment.transaction'].sudo()._process(
            'adyen', dict(response_content, merchantReference=reference),  # Match the transaction
        )

        return response_content

    @http.route('/payment/adyen/return', type='http', auth='public', csrf=False, save_session=False)
    def adyen_return_from_3ds_auth(self, **data):
        """ Process the authentication data sent by Adyen after redirection from the 3DS1 page.

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user if they are redirected to this route with a POST request. Indeed, as the session
        cookie is created without a `SameSite` attribute, some browsers that don't implement the
        recommended default `SameSite=Lax` behavior will not include the cookie in the redirection
        request from the payment provider to Odoo. As the redirection to the '/payment/status' page
        will satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.

        :param dict data: The authentication result data. May include custom params sent to Adyen in
                          the request to allow matching the transaction when redirected here.
        """
        # Retrieve the transaction based on the reference included in the return url
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference('adyen', data)
        if not tx_sudo:
            return request.redirect('/payment/status')

        # Overwrite the operation to force the flow to 'redirect'. This is necessary because even
        # though Adyen is implemented as a direct payment provider, it will redirect the user out
        # of Odoo in some cases. For instance, when a 3DS1 authentication is required, or for
        # special payment methods that are not handled by the drop-in (e.g. Sofort).
        tx_sudo.operation = 'online_redirect'

        # Query and process the result of the additional actions that have been performed
        _logger.info(
            "Handling redirection from Adyen for transaction %s with data:\n%s",
            tx_sudo.reference, pprint.pformat(data)
        )
        self.adyen_payment_details(
            tx_sudo.provider_id.id,
            data['merchantReference'],
            {
                'details': {
                    'redirectResult': data['redirectResult'],
                },
            },
        )

        # Redirect the user to the status page
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def adyen_webhook(self):
        """ Process the data sent by Adyen to the webhook based on the event code.

        See https://docs.adyen.com/development-resources/webhooks/understand-notifications for the
        exhaustive list of event codes.

        :return: The '[accepted]' string to acknowledge the notification
        :rtype: str
        """
        data = request.get_json_data()
        for notification_item in data['notificationItems']:
            payment_data = notification_item['NotificationRequestItem']

            _logger.info(
                "notification received from Adyen with data:\n%s", pprint.pformat(payment_data)
            )
            # Check the integrity of the notification.
            tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
                'adyen', payment_data
            )
            if tx_sudo:
                self._verify_signature(payment_data, tx_sudo)

                # Check whether the event of the notification succeeded and reshape the notification
                # data for parsing
                success = payment_data['success'] == 'true'
                event_code = payment_data['eventCode']
                if event_code == 'AUTHORISATION' and success:
                    payment_data['resultCode'] = 'Authorised'
                elif event_code == 'CANCELLATION':
                    payment_data['resultCode'] = 'Cancelled' if success else 'Error'
                elif event_code in ['REFUND', 'CAPTURE']:
                    payment_data['resultCode'] = 'Authorised' if success else 'Error'
                elif event_code == 'CAPTURE_FAILED' and success:
                    # The capture failed after a capture notification with success = True was sent
                    payment_data['resultCode'] = 'Error'
                else:
                    continue  # Don't handle unsupported event codes and failed events
                tx_sudo._process('adyen', payment_data)
        return request.make_json_response('[accepted]')  # Acknowledge the notification

    @staticmethod
    def _verify_signature(payment_data, tx_sudo):
        """Check that the received signature matches the expected one.

        :param dict payment_data: The payment data containing the received signature.
        :param payment.transaction tx_sudo: The sudoed transaction referenced by the payment data.
        :return: None
        :raise Forbidden: If the signatures don't match.
        """
        # Retrieve the received signature from the payload
        received_signature = payment_data.get('additionalData', {}).get('hmacSignature')
        if not received_signature:
            _logger.warning("received payment data with missing signature")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the payload
        hmac_key = tx_sudo.provider_id.adyen_hmac_key
        expected_signature = AdyenController._compute_signature(payment_data, hmac_key)
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("received payment data with invalid signature")
            raise Forbidden()

    @staticmethod
    def _compute_signature(payload, hmac_key):
        """ Compute the signature from the payload.

        See https://docs.adyen.com/development-resources/webhooks/verify-hmac-signatures

        :param dict payload: The notification payload
        :param str hmac_key: The HMAC key of the provider handling the transaction
        :return: The computed signature
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
        return base64.b64encode(binary_hmac.digest()).decode()
