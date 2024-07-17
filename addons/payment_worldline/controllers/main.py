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

    @http.route(
        _return_url, type='http', auth='public', methods=['GET'], csrf=False, save_session=False
    )
    def worldline_return_from_checkout(self, **data):
        """ Process the notification data sent by Worldline after redirection.

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user if they are redirected to this route with a POST request. Indeed, as the session
        cookie is created without a `SameSite` attribute, some browsers that don't implement the
        recommended default `SameSite=Lax` behavior will not include the cookie in the redirection
        request from the payment provider to Odoo. As the redirection to the '/payment/status' page
        will satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.

        :param dict data: The notification data.
        """
        _logger.info("Handling redirection from Worldline with data:\n%s", pprint.pformat(data))

        provider_id = int(data['provider'])
        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id)
        if not provider_sudo or provider_sudo.code != 'worldline':
            _logger.warning("received data with invalid provider")
            raise Forbidden()

        session_info = provider_sudo._worldline_fetch_session_info(data)
        notification_data = session_info.get('createdPaymentOutput', {})

        # Check the integrity of the notification.
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'worldline', notification_data
        )

        # Handle the notification data.
        tx_sudo._handle_notification_data('worldline', notification_data)
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def worldline_webhook(self):
        """ Process the notification data sent by Worldline to the webhook.

        See https://docs.direct.worldline-solutions.com/en/integration/api-developer-guide/webhooks

        :param dict data: The notification data.
        :return: The '' string to acknowledge the notification
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

        return ''  # Acknowledge the notification.

    @staticmethod
    def _verify_notification_signature(request_data, received_signature, tx_sudo):
        """ Check that the received signature matches the expected one.

        :param dict|bytes request_data: The request data.
        :param str received_signature: The signature to compare with the expected signature.
        :param recordset tx_sudo: The sudoed transaction referenced by the notification data, as a
                                  `payment.transaction` record
        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the signatures don't match
        """
        # Retrieve the received signature from the payload
        if not received_signature:
            _logger.warning("received notification with missing signature")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the payload
        webhook_secret = tx_sudo.provider_id.worldline_webhook_secret
        unencoded_result = hmac.new(webhook_secret.encode(), request_data, hashlib.sha256).digest()
        expected_signature = b64encode(unencoded_result)
        if not hmac.compare_digest(received_signature.encode(), expected_signature):
            _logger.warning("received notification with invalid signature")
            raise Forbidden()
