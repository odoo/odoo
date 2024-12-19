# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import json
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment_paymob import const


_logger = logging.getLogger(__name__)


class PaymobController(http.Controller):
    _return_url = '/payment/paymob/return'
    _webhook_url = '/payment/paymob/webhook'

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def paymob_return_from_checkout(self, **data):
        """ Process the notification data sent by Paymob after redirection from checkout.

        :param dict data: The notification data.
        """
        _logger.info("Handling redirection from Paymob with data:\n%s", pprint.pformat(data))
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'paymob', data
        )
        self._verify_notification_signature(data, tx_sudo)
        tx_sudo._handle_notification_data('paymob', data)
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def paymob_webhook(self, **data):
        """ Process the notification data sent by Paymob to the webhook.

        :param dict data: The notification data.
        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        notification_data = request.get_json_data().get('obj')
        _logger.info(
            "Notification received from Paymob with data:\n%s", pprint.pformat(notification_data)
        )
        try:
            normalized_data = self._normalize_response(notification_data, data.get('hmac'))
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'paymob', normalized_data
            )
            self._verify_notification_signature(data, tx_sudo)
            tx_sudo._handle_notification_data('paymob', normalized_data)
        except ValidationError:  # Acknowledge the notification to avoid getting spammed.
            _logger.exception("Unable to handle the notification data.")
        return ''  # Acknowledge the notification

    @staticmethod
    def _normalize_response(notification_data, hmac_sig):
        """ Normalize the notification data received from Paymob.

        Convert webhook data (which returns a dict with parsed values) and redirect response (which
        returns strings for all values and json-formatted booleans like 'false' for False) into a
        consistent format.

        :param dict notification_data: The notification data received.
        :param str hmac_sig: The HMAC signature returned in the params.
        :return: The normalized response.
        :rtype: dict
        """
        response = {}
        for field in const.SIGNATURE_FIELDS:
            if isinstance(notification_data.get(field), bool):
                response[field] = json.dumps(notification_data.get(field))
            else:
                response[field] = str(notification_data.get(field, 'false'))

        order_data = notification_data.get('order', {})
        response.update({
            'data.message': notification_data.get('data').get('message'),
            'hmac': hmac_sig,
            'order': str(order_data.get('id')),
            'merchant_order_id': order_data.get('merchant_order_id'),
            'source_data.pan': notification_data.get('source_data', {}).get('pan'),
            'source_data.sub_type': notification_data.get('source_data', {}).get('sub_type'),
            'source_data.type': notification_data.get('source_data', {}).get('type'),
        })
        return response

    def _verify_notification_signature(self, notification_data, tx_sudo):
        """ Check that the received signature matches the expected one.

        :param dict notification_data: The notification payload containing the received signature.
        :return: None
        :raise Forbidden: If the signatures don't match.
        """
        # Retrieve the received signature from the payload
        received_signature = notification_data.get('hmac', '')
        if not received_signature:
            _logger.warning("Received notification with missing signature.")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the payload.
        hmac_key = tx_sudo.provider_id.paymob_hmac_key
        expected_signature = self._compute_signature(notification_data, hmac_key)
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("Received notification with invalid signature.")
            raise Forbidden()

    @staticmethod
    def _compute_signature(payload, hmac_key):
        """ Compute the signature from the payload.

        See https://developers.paymob.com/pak/manage-callback/hmac-calculation.

        :param dict payload: The notification payload.
        :param str hmac_key: The HMAC key of the provider handling the transaction.
        :return: The computed signature.
        :rtype: str
        """
        # Concatenate relevant fields used to check for signature and if not found add "false"
        signing_string = ''.join(
            payload.get(field, 'false') for field in const.SIGNATURE_FIELDS
        ).encode('utf-8')
        # Calculate the signature using the hmac_key with SHA-512.
        signed_hmac = hmac.new(hmac_key.encode('utf-8'), signing_string, hashlib.sha512)
        # Calculate the signature by encoding the result with base16.
        return signed_hmac.hexdigest()
