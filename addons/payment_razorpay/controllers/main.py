import pprint

from odoo import http
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


class RazorpayController(http.Controller):
    _return_url = "/payment/razorpay/return"
    _webhook_url = "/payment/razorpay/webhook"

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        _return_url,
        type="http",
        auth="receiver",
        receiver="payment.transaction:_receiver_for_razorpay_return",
        methods=["POST"],
        csrf=False,
        save_session=False,
        typed=True,
    )
    def razorpay_return_from_checkout(self, reference: str, **data):
        """Process the payment data sent by Razorpay after redirection from checkout.

        The route is configured with save_session=False to prevent Odoo from creating a new session
        when the user is redirected here via a POST request. Indeed, as the session cookie is
        created without a `SameSite` attribute, some browsers that don't implement the recommended
        default `SameSite=Lax` behavior will not include the cookie in the redirection request from
        the payment provider to Odoo. However, the redirection to the /payment/status page will
        satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.

        :param str reference: The transaction reference embedded in the return URL.
        :param dict data: The payment data.
        """
        _logger.info(
            "Handling redirection from Razorpay with data:\n%s", pprint.pformat(data)
        )
        request.admission.subject._process("razorpay", request.admission.extra["data"])
        return request.redirect("/payment/status")

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        _webhook_url,
        type="http",
        methods=["POST"],
        auth="receiver",
        receiver="payment.transaction:_receiver_for_razorpay_webhook",
        csrf=False,
        typed=True,
    )
    def razorpay_webhook(self):
        """Process the payment data sent by Razorpay to the webhook.

        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        _logger.info(
            "Notification received from Razorpay with data:\n%s",
            pprint.pformat(request.get_json_data()),
        )
        request.admission.subject._process("razorpay", request.admission.extra["data"])
        return request.prepare_json_response("")
