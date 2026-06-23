# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import pprint

from odoo import http
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_qfpay import const

_logger = get_payment_logger(__name__)


class QFPayController(http.Controller):
    @http.route(const.PAYMENT_RETURN_ROUTE, type="http", auth="public", methods=["GET"])
    def qfpay_return_from_checkout(self, **data):
        """Reconcile transaction status via enquiry and redirect to payment status page."""
        _logger.info("QFPay: Handling redirection with data:\n%s", pprint.pformat(data))
        tx_sudo = request.env["payment.transaction"].sudo()._search_by_reference("qfpay", data)
        if tx_sudo and tx_sudo.state not in ("done", "cancel", "error"):
            payment_data = tx_sudo._qfpay_query_transaction_data()
            if payment_data:
                tx_sudo._record(payment_data)
        return request.redirect("/payment/status")

    @http.route(const.WEBHOOK_ROUTE, type="http", auth="public", methods=["POST"], csrf=False)
    def qfpay_webhook(self):
        """Process the notification data sent by QFPay to the webhook.

        :return: The 'SUCCESS' string to acknowledge the notification.
        :rtype: str
        """
        raw_body = request.httprequest.get_data()
        data = json.loads(raw_body.decode("utf-8"))
        _logger.info("QFPay: Notification received with data:\n%s", pprint.pformat(data))
        tx_sudo = request.env["payment.transaction"].sudo()._search_by_reference("qfpay", data)
        if tx_sudo:
            expected_signature = tx_sudo.provider_id._qfpay_calculate_signature(
                signing_string=raw_body
            )
            received_signature = request.httprequest.headers.get("X-QF-SIGN")
            payment_utils.verify_signature(received_signature, expected_signature)
            tx_sudo._record(data)
        return "SUCCESS"
