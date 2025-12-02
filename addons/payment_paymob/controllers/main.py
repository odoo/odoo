# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import json
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_paymob import const


_logger = get_payment_logger(__name__)


class PaymobController(http.Controller):
    _return_url = '/payment/paymob/return'
    _webhook_url = '/payment/paymob/webhook'

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def paymob_return_from_checkout(self, **data):
        """Process the payment data sent by Paymob after redirection from checkout.

        :param dict data: The payment data.
        """
        _logger.info("Handling redirection from Paymob with data:\n%s", pprint.pformat(data))
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference('paymob', data)
        if tx_sudo:
            self._verify_signature(data, tx_sudo)
            tx_sudo._process('paymob', data)
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def paymob_webhook(self, **data):
        """Process the payment data sent by Paymob to the webhook.

        :param dict data: The payment data.
        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        payment_data = request.get_json_data().get('obj')
        _logger.info(
            "Notification received from Paymob with data:\n%s", pprint.pformat(payment_data)
        )
        normalized_data = self._normalize_response(payment_data, data.get('hmac'))
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
            'paymob', normalized_data
        )
        if tx_sudo:
            self._verify_signature(data, tx_sudo)
            tx_sudo._process('paymob', normalized_data)
        return ''  # Acknowledge the notification

    @staticmethod
    def _normalize_response(payment_data, hmac_sig):
        """Normalize the payment data received from Paymob.

        Convert webhook data (which returns a dict with parsed values) and redirect response (which
        returns strings for all values and json-formatted booleans like 'false' for False) into a
        consistent format.

        :param dict payment_data: The payment data received.
        :param str hmac_sig: The HMAC signature returned in the params.
        :return: The normalized response.
        :rtype: dict
        """
        response = {}
        for field in const.SIGNATURE_FIELDS:
            if isinstance(payment_data.get(field), bool):
                response[field] = json.dumps(payment_data.get(field))
            else:
                response[field] = str(payment_data.get(field, 'false'))

        order_data = payment_data.get('order', {})
        response.update({
            'data.message': payment_data.get('data').get('message'),
            'hmac': hmac_sig,
            'order': str(order_data.get('id')),
            'merchant_order_id': order_data.get('merchant_order_id'),
            'source_data.pan': payment_data.get('source_data', {}).get('pan'),
            'source_data.sub_type': payment_data.get('source_data', {}).get('sub_type'),
            'source_data.type': payment_data.get('source_data', {}).get('type'),
        })
        return response

    def _verify_signature(self, payment_data, tx_sudo):
        """Check that the received signature matches the expected one.

        :param dict payment_data: The notification payload containing the received signature.
        :param payment.transaction tx_sudo: The sudoed transaction referenced by the payment data.
        :return: None
        :raise Forbidden: If the signatures don't match.
        """
        # Retrieve the received signature from the payload
        received_signature = payment_data.get('hmac', '')
        if not received_signature:
            _logger.warning("Received payment data with missing signature.")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the payload.
        hmac_key = tx_sudo.provider_id.paymob_hmac_key
        expected_signature = self._compute_signature(payment_data, hmac_key)
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("Received payment data with invalid signature.")
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
