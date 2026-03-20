# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import json
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger


_logger = get_payment_logger(__name__)


class FlutterwaveController(http.Controller):
    _return_url = '/payment/flutterwave/return'
    _auth_return_url = '/payment/flutterwave/auth_return'
    _webhook_url = '/payment/flutterwave/webhook'

    @http.route(_return_url, type='http', methods=['GET'], auth='public')
    def flutterwave_return_from_checkout(self, **data):
        """Process the payment data sent by Flutterwave after redirection from checkout.

        :param dict data: The payment data.
        """
        _logger.info("Handling redirection from Flutterwave with data:\n%s", pprint.pformat(data))

        if data.get('status') != 'cancelled':
            self._verify_and_process(data)
        else:  # The customer cancelled the payment by clicking on the close button.
            pass  # Don't try to process this case because the transaction id was not provided.

        # Redirect the user to the status page.
        return request.redirect('/payment/status')

    @http.route(_auth_return_url, type='http', methods=['GET'], auth='public')
    def flutterwave_return_from_authorization(self, response=None):
        """ Process the response sent by Flutterwave after authorization.

        :param str response: The stringified JSON response.
        """
        data = json.loads(response) if response else {}
        return self.flutterwave_return_from_checkout(**data)

    @http.route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def flutterwave_webhook(self):
        """Process the payment data sent by Flutterwave to the webhook.

        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        data = request.get_json_data()
        _logger.info("Notification received from Flutterwave with data:\n%s", pprint.pformat(data))

        if data['event'] == 'charge.completed':
            payment_data = data['data']
            tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
                'flutterwave', payment_data
            )
            if tx_sudo:
                signature = request.httprequest.headers.get('verif-hash')
                self._verify_signature(signature, tx_sudo)
            tx_sudo._process('flutterwave', payment_data)
        return request.make_json_response('')

    @staticmethod
    def _verify_signature(received_signature, tx_sudo):
        """Check that the received signature matches the expected one.

        :param dict received_signature: The signature received with the payment data.
        :param payment.transaction tx_sudo: The sudoed transaction referenced by the payment data.
        :return: None
        :raise Forbidden: If the signatures don't match.
        """
        # Check for the received signature.
        if not received_signature:
            _logger.warning("Received payment data with missing signature.")
            raise Forbidden()

        # Compare the received signature with the expected signature.
        expected_signature = tx_sudo.provider_id.flutterwave_webhook_secret
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("Received payment data with invalid signature.")
            raise Forbidden()

    @staticmethod
    def _verify_and_process(data):
        """Verify and process the payment data sent by Flutterwave.

        :param dict data: The payment data.
        :return: None
        """
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
            'flutterwave', data
        )
        if not tx_sudo:
            return

        try:
            verified_data = tx_sudo._send_api_request(
                'GET', 'transactions/verify_by_reference', params={'tx_ref': tx_sudo.reference},
            )
        except ValidationError:
            _logger.error("Unable to verify the payment data")
        else:
            tx_sudo._process('flutterwave', verified_data)
