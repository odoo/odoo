# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_sslcommerz import const

_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class SSLCommerzController(http.Controller):
    @http.route(
        const.PAYMENT_RETURN_ROUTE,
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def sslcommerz_return_from_checkout(self, **data):
        """Process the payment data sent by SSLCOMMERZ after redirection from checkout.

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user if they are redirected to this route with a POST request. Indeed, as the session
        cookie is created without a `SameSite` attribute, some browsers that don't implement the
        recommended default `SameSite=Lax` behavior will not include the cookie in the redirection
        request from the payment provider to Odoo. As the redirection to the '/payment/status' page
        will satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.

        :param dict data: The payment data.
        """
        _logger.info("Handling redirection from SSLCOMMERZ with data:\n%s", pprint.pformat(data))
        self._verify_and_process(data)
        return request.redirect("/payment/status")

    @http.route(const.IPN_ROUTE, type="http", auth="public", methods=["POST"], csrf=False)
    def sslcommerz_ipn(self, **data):
        """Process the payment data sent by SSLCOMMERZ through the IPN (Instant Payment
        Notification), SSLCOMMERZ's server-to-server equivalent of a webhook.

        :param dict data: The payment data.
        :return: An empty response to acknowledge the notification.
        :rtype: str
        """
        _logger.info("Notification received from SSLCOMMERZ with data:\n%s", pprint.pformat(data))
        self._verify_and_process(data)
        return ""

    def _verify_and_process(self, data):
        """Verify the payment data and record the transaction update, if any.

        :param dict data: The payment data.
        :return: None
        """
        tx_sudo = self.env["payment.transaction"].sudo()._search_by_reference("sslcommerz", data)
        if not tx_sudo:
            return
        # SSLCOMMERZ only issues a val_id for successful transactions, and the Order Validation
        # API is the only verification mechanism available, so a notification without one can't
        # be verified.
        if val_id := data.get("val_id"):
            try:
                verified_data = tx_sudo._send_api_request(
                    "GET",
                    "/validator/api/validationserverAPI.php",
                    params={
                        "val_id": val_id,
                        "store_id": tx_sudo.provider_id.sslcommerz_store_id,
                        "store_passwd": tx_sudo.provider_id.sslcommerz_store_password,
                    },
                )
            except ValidationError:
                _logger.error("Unable to process the payment data.")
            else:
                if verified_data.get("tran_id") != tx_sudo.reference:
                    raise Forbidden
                tx_sudo._record(verified_data)
        else:
            _logger.warning(
                "Received data without a val_id for transaction %s; skipping the verification.",
                tx_sudo.reference,
            )
