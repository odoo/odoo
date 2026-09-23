import pprint

from odoo import http
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


class RedsysController(http.Controller):
    _return_url = "/payment/redsys/return"
    _webhook_url = "/payment/redsys/webhook"

    @http.route(
        _return_url,
        type="http",
        auth="receiver",
        receiver="payment.transaction:_receiver_for_redsys_return",
        methods=["GET"],
        typed=True,
    )
    def redsys_return_from_checkout(self, **encoded_data):
        """Process the payment data sent by Redsys after redirection.

        :param dict encoded_data: The encoded payment data.
        """
        data = request.admission.extra["data"]
        _logger.info(
            "Handling redirection from Redsys with data:\n%s", pprint.pformat(data)
        )
        request.admission.subject._process("redsys", data)
        return request.redirect("/payment/status")

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        _webhook_url,
        type="http",
        auth="receiver",
        receiver="payment.transaction:_receiver_for_redsys_webhook",
        methods=["POST"],
        csrf=False,
        typed=True,
    )
    def redsys_webhook(self, **encoded_data):
        """Process the payment data sent by Redsys to the webhook.

        :param dict encoded_data: The encoded payment data.
        :return: The 'OK' string to acknowledge the notification.
        :rtype: str
        """
        data = request.admission.extra["data"]
        _logger.info(
            "Received webhook notification from Redsys:\n%s", pprint.pformat(data)
        )
        request.admission.subject._process("redsys", data)
        return ""
