# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
import pprint

import werkzeug
from werkzeug import urls

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools.pycompat import to_text

import odoo.addons.payment.utils as payment_utils
from odoo.addons.payment_adyen.models.payment_acquirer import CURRENCY_DECIMALS

_logger = logging.getLogger(__name__)


class AdyenController(http.Controller):

    @http.route('/payment/adyen/payment_methods', type='json', auth='public')
    def payment_methods(
        self, acquirer_id, amount=None, currency_id=None, partner_id=None
    ):
        """ Query the available payment methods based on the transaction context.

        :param int acquirer_id: The acquirer handling the transaction, as a `payment.acquirer` id
        :param float|None amount: The transaction amount
        :param int|None currency_id: The transaction currency, as a `res.currency` id
        :param int|None partner_id: The partner making the transaction, as a `res.partner` id
        :return: The JSON-formatted content of the response
        :rtype: dict
        """
        acquirer_sudo = request.env['payment.acquirer'].sudo().browse(acquirer_id)
        currency = request.env['res.currency'].browse(currency_id)
        currency_code = currency_id and currency.name
        converted_amount = amount and currency_code and payment_utils.convert_to_minor_units(
            amount, currency, CURRENCY_DECIMALS.get(currency_code)
        )
        partner_sudo = partner_id and request.env['res.partner'].browse(partner_id).sudo()
        partner_country_code = partner_sudo and partner_sudo.country_id.code
        # The lang is taken from the context rather than from the partner because it is not required
        # to be logged to make a payment and because the lang is not always set on the partner.
        # Adyen only supports a reduced set of languages but, instead of looking for the closest
        # match in https://docs.adyen.com/checkout/components-web/localization-components, we simply
        # provide the lang string as is (after adapting the format) and let Adyen find the best fit.
        lang_code = request.context.get('lang', 'en-US').replace('_', '-')
        shopper_reference = partner_sudo and f'ODOO_PARTNER_{partner_sudo.id}'
        data = {
            'merchantAccount': acquirer_sudo.adyen_merchant_account,
            'amount': converted_amount,
            'countryCode': partner_country_code,  # ISO 3166-1 alpha-2 (e.g.: 'BE')
            'shopperLocale': lang_code,  # IETF language tag (e.g.: 'fr-BE')
            'shopperReference': shopper_reference,
            'channel': 'Web',
        }
        response_content = acquirer_sudo._adyen_make_request(
            base_url=acquirer_sudo.adyen_checkout_api_url,
            endpoint_key='payment_methods',
            payload=data,
            method='POST'
        )
        return response_content

    @http.route('/payment/adyen/origin_key', type='json', auth='public')
    def origin_key(self, acquirer_id):
        """ Request an origin key based on the current domain.

        :param int acquirer_id: The acquirer handling the transaction, as a `payment.acquirer` id
        :return: The JSON-formatted content of the response
        :rtype: dict
        """
        acquirer_sudo = request.env['payment.acquirer'].browse(acquirer_id).sudo()
        domain = acquirer_sudo._get_base_url()
        data = {
            'originDomains': [domain],
        }
        response_content = acquirer_sudo._adyen_make_request(
            base_url=acquirer_sudo.adyen_checkout_api_url,
            endpoint_key='origin_keys',
            payload=data,
            method='POST'
        )
        return response_content

    @http.route('/payment/adyen/payments', type='json', auth='public')
    def process_payment(
        self, acquirer_id, reference, converted_amount, currency_id, partner_id, payment_method,
        access_token, browser_info=None
    ):
        """ Make a payment request and handle the response.

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
        db_secret = request.env['ir.config_parameter'].sudo().get_param('database.secret')
        if not payment_utils.check_access_token(
            access_token, db_secret, reference, converted_amount, partner_id
        ):
            raise ValidationError("Adyen: " + _("Received tampered payment request data."))

        # Make the payment request to Adyen
        acquirer_sudo = request.env['payment.acquirer'].sudo().browse(acquirer_id)
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
            'shopperInteraction': 'Ecommerce',
            'storePaymentMethod': tx_sudo.tokenize,  # True by default on Adyen side
            'additionalData': {
                'allow3DS2': True
            },
            'channel': 'web',  # Required to support 3DS
            'origin': acquirer_sudo._get_base_url(),  # Required to support 3DS
            'browserInfo': browser_info,  # Required to support 3DS
            'returnUrl': urls.url_join(
                acquirer_sudo._get_base_url(),
                # Include the reference in the return url to be able to match it after redirection.
                # The key 'merchantReference' is chosen on purpose to be the same than that returned
                # by the /payments endpoint of Adyen.
                f'/payment/adyen/return?merchantReference={reference}'
            ),
        }
        response_content = acquirer_sudo._adyen_make_request(
            base_url=acquirer_sudo.adyen_checkout_api_url,
            endpoint_key='payments',
            payload=data,
            method='POST'
        )

        # Handle the payment request response
        _logger.info(f"payment request response:\n{pprint.pformat(response_content)}")
        request.env['payment.transaction'].sudo()._handle_feedback_data(
            dict(response_content, merchantReference=reference),  # Allow matching the transaction
            'adyen'
        )
        if 'action' in response_content and response_content['action']['type'] == 'redirect':
            tx_sudo.adyen_payment_data = response_content['paymentData']

        return response_content

    @http.route('/payment/adyen/payment_details', type='json', auth='public')
    def payment_details(self, acquirer_id, reference, details, payment_data):
        """ Query the status of a transaction that required additional actions and process it.

         The additional actions can have been performed both from the inline form or during a
         redirection.

        :param int acquirer_id: The acquirer handling the transaction, as a `payment.acquirer` id
        :param str reference: The reference of the transaction
        :param dict details: The specification of the additional actions
        :param str payment_data: The encrypted payment data of the transaction
        :return: The JSON-formatted content of the response
        :rtype: dict
        """
        # Make the payment details request to Adyen
        acquirer_sudo = request.env['payment.acquirer'].browse(acquirer_id).sudo()
        data = {
            'details': details,
            'paymentData': payment_data,
        }
        response_content = acquirer_sudo._adyen_make_request(
            base_url=acquirer_sudo.adyen_checkout_api_url,
            endpoint_key='payments_details',
            payload=data,
            method='POST'
        )

        # Handle the payment details request response
        _logger.info(f"payment details request response:\n{pprint.pformat(response_content)}")
        request.env['payment.transaction'].sudo()._handle_feedback_data(
            dict(response_content, merchantReference=reference),  # Allow matching the transaction
            'adyen'
        )

        return response_content

    @http.route('/payment/adyen/return', type='http', auth='public', csrf=False)
    def return_from_redirect(self, **data):
        """ Process the data returned by Adyen after redirection.

        :param dict data: Feedback data. May include custom params sent to Adyen in the request to
                          allow matching the transaction when redirected here.
        """
        # Retrieve the transaction based on the reference included in the return url
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_data(data, 'adyen')
        # Overwrite the operation to force the flow to 'redirect'. This is necessary because even
        # thought Adyen is implemented as a direct payment provider, it will redirect the user out
        # of Odoo in some cases. For instance, when a 3DS1 authentication is required, or for
        # special payment methods that are not handled by the drop-in (e.g. Sofort).
        tx_sudo.operation = 'online_redirect'
        # Query and process the result of the additional actions that have been performed
        self.payment_details(
            tx_sudo.acquirer_id.id,
            data['merchantReference'],
            {detail: value for detail, value in data.items() if detail != 'merchantReference'},
            tx_sudo.adyen_payment_data,
        )
        # Redirect the user to the status page
        return werkzeug.utils.redirect('/payment/status')

    @http.route(
        '/payment/adyen/notification', type='json', auth='public', methods=['POST'], csrf=False
    )
    def notification(self):
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
            hmac_signature = notification_data.get('additionalData', {}).get('hmacSignature')
            if not hmac_signature:
                _logger.warning(f"ignored notification with missing signature")
                continue
            acquirer_sudo = request.env['payment.transaction'].sudo()._get_tx_from_data(
                notification_data, 'adyen'
            ).acquirer_id  # Find the acquirer based on the transaction
            if hmac_signature != to_text(acquirer_sudo._adyen_compute_signature(notification_data)):
                _logger.warning(f"ignored notification with invalid signature")
                continue

            _logger.info(f"notification received:\n{pprint.pformat(notification_data)}")
            if notification_data['success'] != 'true':
                continue  # Don't handle failed events

            # Reshape the notification data for parsing
            event_code = notification_data['eventCode']
            if event_code == 'AUTHORISATION':
                notification_data['resultCode'] = 'Authorised'
            elif event_code == 'CANCELLATION':
                notification_data['resultCode'] = 'Cancelled'
            else:
                continue  # Don't handle unsupported event codes

            # Handle the notification data as a regular feedback
            request.env['payment.transaction'].sudo()._handle_feedback_data(
                notification_data, 'adyen'
            )

        return '[accepted]'  # Acknowledge the notification
