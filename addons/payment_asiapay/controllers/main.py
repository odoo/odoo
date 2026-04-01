# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger


_logger = get_payment_logger(__name__)


class AsiaPayController(http.Controller):
    _return_url = '/payment/asiapay/return'
    _webhook_url = '/payment/asiapay/webhook'

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def asiapay_return_from_checkout(self, **data):
        """Process the payment data sent by AsiaPay after redirection.

        :param dict data: The payment data.
        """
        # Don't process the payment data as they contain no valuable information except for the
        # reference and AsiaPay doesn't expose an endpoint to fetch the data from the API.
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def asiapay_webhook(self, **data):
        """Process the payment data sent by AsiaPay to the webhook.

        :param dict data: The payment data.
        :return: The 'OK' string to acknowledge the notification.
        :rtype: str
        """
        _logger.info("Notification received from AsiaPay with data:\n%s", pprint.pformat(data))
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference('asiapay', data)
        if tx_sudo:
            self._verify_signature(data, tx_sudo)
            tx_sudo._process('asiapay', data)
        return 'OK'  # Acknowledge the notification.

    @staticmethod
    def _verify_signature(payment_data, tx_sudo):
        """Check that the received signature matches the expected one.

        :param dict payment_data: The payment data.
        :param payment.transaction tx_sudo: The sudoed transaction referenced by the payment data.
        :return: None
        :raise Forbidden: If the signatures don't match.
        """
        received_signature = payment_data.get('secureHash')
        if not received_signature:
            _logger.warning("Received payment data with missing signature.")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the data.
        expected_signature = tx_sudo.provider_id._asiapay_calculate_signature(
            payment_data, incoming=True
        )
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("Received payment data with invalid signature.")
            raise Forbidden()
