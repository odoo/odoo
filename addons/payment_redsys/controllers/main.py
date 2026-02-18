# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import pprint

from odoo import http
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger


_logger = get_payment_logger(__name__)


class RedsysController(http.Controller):
    _return_url = '/payment/redsys/return'
    _webhook_url = '/payment/redsys/webhook'

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def redsys_return_from_checkout(self, **encoded_data):
        """Process the payment data sent by Redsys after redirection.

        :param dict encoded_data: The encoded payment data.
        """
        data = json.loads(base64.b64decode(encoded_data['Ds_MerchantParameters']).decode())
        _logger.info("Handling redirection from Redsys with data:\n%s", pprint.pformat(data))
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference('redsys', data)
        if tx_sudo:
            self._verify_signature(encoded_data, tx_sudo)
            tx_sudo._process('redsys', data)
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def redsys_webhook(self, **encoded_data):
        """Process the payment data sent by Redsys to the webhook.

        :param dict encoded_data: The encoded payment data.
        :return: The 'OK' string to acknowledge the notification.
        :rtype: str
        """
        data = json.loads(base64.b64decode(encoded_data.get('Ds_MerchantParameters')).decode())
        _logger.info("Received webhook notification from Redsys:\n%s", pprint.pformat(data))
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference('redsys', data)
        if tx_sudo:
            self._verify_signature(encoded_data, tx_sudo)
            tx_sudo._process('redsys', data)
        return ''

    @staticmethod
    def _verify_signature(payment_data, tx_sudo):
        """Check that the received signature matches the expected one.

        :param dict payment_data: The payment data to verify.
        :param payment.transaction tx_sudo: The transaction referenced by the payment data.
        :return: None
        :raise Forbidden: If the signatures don't match.
        """
        received_signature = payment_data.get('Ds_Signature')
        expected_signature = tx_sudo.provider_id._redsys_calculate_signature(
            payment_data.get('Ds_MerchantParameters'),
            tx_sudo.reference,
            tx_sudo.provider_id.redsys_secret_key,
        )
        payment_utils.verify_signature(received_signature, expected_signature)
