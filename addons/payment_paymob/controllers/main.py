import pprint

from odoo import http
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


class PaymobController(http.Controller):
    _return_url = "/payment/paymob/return"
    _webhook_url = "/payment/paymob/webhook"

    @http.route(
        _return_url,
        type="http",
        auth="receiver",
        receiver="payment.transaction:_receiver_for_paymob_return",
        methods=["GET"],
        typed=True,
    )
    def paymob_return_from_checkout(self, **data):
        """Process the payment data sent by Paymob after redirection from checkout.

        :param dict data: The payment data.
        """
        _logger.info(
            "Handling redirection from Paymob with data:\n%s", pprint.pformat(data)
        )
        request.admission.subject._process("paymob", request.admission.extra["data"])
        return request.redirect("/payment/status")

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        _webhook_url,
        type="http",
        auth="receiver",
        receiver="payment.transaction:_receiver_for_paymob_webhook",
        methods=["POST"],
        csrf=False,
        typed=True,
    )
    def paymob_webhook(self, **data):
        """Process the payment data sent by Paymob to the webhook.

        :param dict data: The payment data.
        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        _logger.info(
            "Notification received from Paymob with data:\n%s",
            pprint.pformat(request.get_json_data().get("obj")),
        )
        request.admission.subject._process("paymob", request.admission.extra["data"])
        return ""  # Acknowledge the notification
