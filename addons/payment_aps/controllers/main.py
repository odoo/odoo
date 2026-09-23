import pprint

from odoo import http
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


class APSController(http.Controller):
    _return_url = "/payment/aps/return"
    _webhook_url = "/payment/aps/webhook"

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        _return_url,
        type="http",
        auth="receiver",
        receiver="payment.transaction:_receiver_for_aps_return",
        methods=["POST"],
        csrf=False,
        save_session=False,
        typed=True,
    )
    def aps_return_from_checkout(self, **data):
        """Process the payment data sent by APS after redirection.

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user if they are redirected to this route with a POST request. Indeed, as the session
        cookie is created without a `SameSite` attribute, some browsers that don't implement the
        recommended default `SameSite=Lax` behavior will not include the cookie in the redirection
        request from the payment provider to Odoo. As the redirection to the '/payment/status' page
        will satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.

        :param dict data: The payment data.
        """
        _logger.info(
            "Handling redirection from APS with data:\n%s", pprint.pformat(data)
        )

        request.admission.subject._process("aps", request.admission.extra["data"])
        return request.redirect("/payment/status")

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        _webhook_url,
        type="http",
        auth="receiver",
        receiver="payment.transaction:_receiver_for_aps_webhook",
        methods=["POST"],
        csrf=False,
        typed=True,
    )
    def aps_webhook(self, **data):
        """Process the payment data sent by APS to the webhook.

        See https://paymentservices-reference.payfort.com/docs/api/build/index.html#transaction-feedback.

        :param dict data: The payment data.
        :return: The 'SUCCESS' string to acknowledge the notification
        :rtype: str
        """
        _logger.info(
            "Notification received from APS with data:\n%s", pprint.pformat(data)
        )
        request.admission.subject._process("aps", request.admission.extra["data"])
        return ""  # Acknowledge the notification.
