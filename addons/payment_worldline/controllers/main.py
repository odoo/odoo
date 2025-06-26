# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode
import hashlib
import hmac
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


_logger = logging.getLogger(__name__)


class WorldlineController(http.Controller):
    _return_url = '/payment/worldline/return'
    _webhook_url = '/payment/worldline/webhook'

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def worldline_return_from_checkout(self, **data):
        """ Process the notification data sent by Worldline after redirection.

        :param dict data: The notification data, including the provider id appended to the URL in
                          `_get_specific_rendering_values`.
        """
        _logger.info("Handling redirection from Worldline with data:\n%s", pprint.pformat(data))

        provider_id = int(data['provider_id'])
        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id).exists()
        if not provider_sudo or provider_sudo.code != 'worldline':
            _logger.warning("Received payment data with invalid provider id.")
            raise Forbidden()

        # Fetch the checkout session data from Worldline.
        checkout_session_data = provider_sudo._worldline_make_request(
            f'hostedcheckouts/{data["hostedCheckoutId"]}', method='GET'
        )
        _logger.info(
            "Response of '/hostedcheckouts/<hostedCheckoutId>' request:\n%s",
            pprint.pformat(checkout_session_data)
        )
        notification_data = checkout_session_data.get('createdPaymentOutput', {})

        # Handle the notification data.
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'worldline', notification_data
        )
        tx_sudo._handle_notification_data('worldline', notification_data)
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def worldline_webhook(self):
        """ Process the notification data sent by Worldline to the webhook.

        See https://docs.direct.worldline-solutions.com/en/integration/api-developer-guide/webhooks.

        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        notification_data = request.get_json_data()
        _logger.info(
            "Notification received from Worldline with data:\n%s", pprint.pformat(notification_data)
        )
        try:
            # Check the integrity of the notification.
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'worldline', notification_data
            )
            received_signature = request.httprequest.headers.get('X-GCS-Signature')
            request_data = request.httprequest.data
            self._verify_notification_signature(request_data, received_signature, tx_sudo)

            # Handle the notification data.
            tx_sudo._handle_notification_data('worldline', notification_data)
        except ValidationError:  # Acknowledge the notification to avoid getting spammed.
            _logger.exception("Unable to handle the notification data; skipping to acknowledge.")

        return request.make_json_response('')  # Acknowledge the notification.

    @staticmethod
    def _verify_notification_signature(request_data, received_signature, tx_sudo):
        """ Check that the received signature matches the expected one.

        :param dict|bytes request_data: The request data.
        :param str received_signature: The signature to compare with the expected signature.
        :param payment.transaction tx_sudo: The sudoed transaction referenced by the notification
                                            data.
        :return: None
        :raise Forbidden: If the signatures don't match.
        """
        # Retrieve the received signature from the payload.
        if not received_signature:
            _logger.warning("Received notification with missing signature.")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the payload.
        webhook_secret = tx_sudo.provider_id.worldline_webhook_secret
        expected_signature = b64encode(
            hmac.new(webhook_secret.encode(), request_data, hashlib.sha256).digest()
        )
        if not hmac.compare_digest(received_signature.encode(), expected_signature):
            _logger.warning("Received notification with invalid signature.")
            raise Forbidden()
