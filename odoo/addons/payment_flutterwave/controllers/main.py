# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import json
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


_logger = logging.getLogger(__name__)


class FlutterwaveController(http.Controller):
    _return_url = '/payment/flutterwave/return'
    _auth_return_url = '/payment/flutterwave/auth_return'
    _webhook_url = '/payment/flutterwave/webhook'

    @http.route(_return_url, type='http', methods=['GET'], auth='public')
    def flutterwave_return_from_checkout(self, **data):
        """ Process the notification data sent by Flutterwave after redirection from checkout.

        :param dict data: The notification data.
        """
        _logger.info("Handling redirection from Flutterwave with data:\n%s", pprint.pformat(data))

        # Handle the notification data.
        if data.get('status') != 'cancelled':
            request.env['payment.transaction'].sudo()._handle_notification_data('flutterwave', data)
        else:  # The customer cancelled the payment by clicking on the close button.
            pass  # Don't try to process this case because the transaction id was not provided.

        # Redirect the user to the status page.
        return request.redirect('/payment/status')

    @http.route(_auth_return_url, type='http', methods=['GET'], auth='public')
    def flutterwave_return_from_authorization(self, response):
        """ Process the response sent by Flutterwave after authorization.

        :param str response: The stringified JSON response.
        """
        data = json.loads(response)
        return self.flutterwave_return_from_checkout(**data)

    @http.route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def flutterwave_webhook(self):
        """ Process the notification data sent by Flutterwave to the webhook.

        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        data = request.get_json_data()
        _logger.info("Notification received from Flutterwave with data:\n%s", pprint.pformat(data))

        if data['event'] == 'charge.completed':
            try:
                # Check the origin of the notification.
                tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                    'flutterwave', data['data']
                )
                signature = request.httprequest.headers.get('verif-hash')
                self._verify_notification_signature(signature, tx_sudo)

                # Handle the notification data.
                notification_data = data['data']
                tx_sudo._handle_notification_data('flutterwave', notification_data)
            except ValidationError:  # Acknowledge the notification to avoid getting spammed.
                _logger.exception("Unable to handle the notification data; skipping to acknowledge")
        return request.make_json_response('')

    @staticmethod
    def _verify_notification_signature(received_signature, tx_sudo):
        """ Check that the received signature matches the expected one.

        :param dict received_signature: The signature received with the notification data.
        :param recordset tx_sudo: The sudoed transaction referenced by the notification data, as a
                                  `payment.transaction` record.
        :return: None
        :raise Forbidden: If the signatures don't match.
        """
        # Check for the received signature.
        if not received_signature:
            _logger.warning("Received notification with missing signature.")
            raise Forbidden()

        # Compare the received signature with the expected signature.
        expected_signature = tx_sudo.provider_id.flutterwave_webhook_secret
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("Received notification with invalid signature.")
            raise Forbidden()
