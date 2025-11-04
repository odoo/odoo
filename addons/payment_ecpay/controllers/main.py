# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class EcpayController(http.Controller):
    _return_url = "/payment/ecpay/return"
    _webhook_url = "/payment/ecpay/webhook"

    @http.route(_return_url, type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def ecpay_return_from_checkout(self, **data):
        """Process the notification data sent by ECPay after redirection.

        :param dict data: The notification data.
        """
        _logger.info("Handling redirection from ECPay with data:\n%s", pprint.pformat(data))
        tx_sudo = request.env["payment.transaction"].sudo()._search_by_reference("ecpay", data)
        if tx_sudo:
            self._verify_signature(data, tx_sudo)
            tx_sudo._process("ecpay", data)
        return request.redirect("/payment/status")

    @http.route(_webhook_url, type="http", auth="public", methods=["POST"], csrf=False)
    def ecpay_webhook(self, **data):
        """Process the notification data sent by ECPay to the webhook.

        :param dict data: The notification data.
        :return: The '1|OK' string to acknowledge the notification.
        :rtype: str
        """
        _logger.info("Notification received from ECPay with data:\n%s", pprint.pformat(data))
        tx_sudo = request.env["payment.transaction"].sudo()._search_by_reference("ecpay", data)
        if tx_sudo:
            self._verify_signature(data, tx_sudo)
            tx_sudo._process("ecpay", data)
        return "1|OK"

    @staticmethod
    def _verify_signature(payment_data, tx_sudo):
        """Check that the received signature matches the expected one.

        :param dict payment_data: The notification data
        :param recordset tx_sudo: The sudoed transaction referenced by the notification data, as a
                                  `payment.transaction` record
        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the signatures don't match
        """
        received_signature = payment_data.get("CheckMacValue")
        if not received_signature:
            _logger.warning("Received payment data with missing signature.")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the data.
        expected_signature = tx_sudo.provider_id._ecpay_calculate_signature(payment_data)
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("Received payment data with invalid signature.")
            raise Forbidden()
