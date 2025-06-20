# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hmac
import json
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


_logger = logging.getLogger(__name__)


class RedsysController(http.Controller):
    _return_url = '/payment/redsys/return'
    _webhook_url = '/payment/redsys/webhook'

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def redsys_return_from_checkout(self, **encoded_data):
        """ Process the notification data sent by Redsys after redirection from checkout.

        :param dict data: The notification data.
        """
        if encoded_data:
            data = json.loads(base64.b64decode(encoded_data.get('Ds_MerchantParameters')).decode())
            _logger.info(
                "Handling redirection from Redsys with data:\n%s",
                pprint.pformat(data)
            )
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'redsys', data
            )
            self._verify_notification_signature(encoded_data, tx_sudo)
            tx_sudo._handle_notification_data('redsys', data)
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def redsys_webhook(self, **encoded_data):
        """ Process the notification data sent by Redsys to the webhook.

        :param dict data: The notification data.
        :return: The 'OK' string to acknowledge the notification.
        :rtype: str
        """
        try:
            data = json.loads(base64.b64decode(encoded_data.get('Ds_MerchantParameters')).decode())
            _logger.info(
                "Notification received from Redsys:\n%s", pprint.pformat(data)
            )
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'redsys', data
            )
            self._verify_notification_signature(encoded_data, tx_sudo)
            tx_sudo._handle_notification_data('redsys', data)
        except ValidationError:  # Acknowledge the notification to avoid getting spammed.
            _logger.exception("Unable to handle the notification data; skipping to acknowledge.")
        # Inform Redsys of the notification processing.
        return 'OK'

    @staticmethod
    def _verify_notification_signature(data, tx_sudo):
        """ Check that the received signature matches the expected one.

        :param dict data: The notification payload containing the received signature
        :param recordset tx_sudo: The sudoed transaction referenced by the notification data, as a
                                  `payment.transaction` record
        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the signatures don't match
        """
        # Retrieve the received signature from the payload
        received_signature = data.get('Ds_Signature')
        if not received_signature:
            _logger.warning("received notification with missing signature")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the payload
        hmac_key = tx_sudo.provider_id.redsys_secret_key
        expected_signature = tx_sudo._redsys_calculate_signature(
            data.get('Ds_MerchantParameters'),
            tx_sudo.reference,
            hmac_key
        )
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("received notification with invalid signature")
            raise Forbidden()
