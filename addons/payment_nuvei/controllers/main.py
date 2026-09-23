import pprint

from odoo import http
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


class NuveiController(http.Controller):
    _return_url = "/payment/nuvei/return"
    _webhook_url = "/payment/nuvei/webhook"

    @http.route(
        _return_url,
        type="http",
        auth="receiver",
        receiver="payment.transaction:_receiver_for_nuvei_return",
        methods=["GET"],
        typed=True,
    )
    def nuvei_return_from_checkout(
        self, tx_ref: str | None = None, error_access_token: str | None = None, **data
    ):
        """Process the payment data sent by Nuvei after redirection.

        :param str tx_ref: The optional reference of the transaction having been canceled/errored.
        :param str error_access_token: The optional access token to verify the authenticity of
                                       requests for errored payments.
        :param dict data: The payment data.
        """
        _logger.info(
            "Handling redirection from Nuvei with data:\n%s", pprint.pformat(data)
        )
        if tx_ref and error_access_token:
            _logger.warning("Nuvei errored on transaction: %s.", tx_ref)
        request.admission.subject._process("nuvei", request.admission.extra["data"])
        return request.redirect("/payment/status")

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        _webhook_url,
        type="http",
        auth="receiver",
        receiver="payment.transaction:_receiver_for_nuvei_webhook",
        methods=["POST"],
        csrf=False,
        typed=True,
    )
    def nuvei_webhook(self, **data):
        """Process the payment data sent by Nuvei to the webhook.

        See https://docs.nuvei.com/documentation/integration/webhooks/payment-dmns/.

        :param dict data: The payment data.
        :return: The 'OK' string to acknowledge the notification.
        :rtype: str
        """
        _logger.info(
            "Notification received from Nuvei with data:\n%s", pprint.pformat(data)
        )
        request.admission.subject._process("nuvei", request.admission.extra["data"])
        return "OK"  # Acknowledge the notification.
