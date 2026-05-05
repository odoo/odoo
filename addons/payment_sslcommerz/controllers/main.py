# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

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
        methods=["GET", "POST"],
        csrf=False,
        save_session=False,
    )
    def sslcommerz_return(self, **data):
        """Process the customer redirection from SSLCOMMERZ for all payment outcomes."""
        _logger.info("Handling redirection from SSLCOMMERZ with data:\n%s", pprint.pformat(data))
        tx_sudo = self.env["payment.transaction"].sudo()._search_by_reference("sslcommerz", data)
        if tx_sudo:
            self._verify_and_process(data, tx_sudo=tx_sudo)
        return request.redirect("/payment/status")

    @http.route(const.IPN_ROUTE, type="http", auth="public", methods=["POST"], csrf=False)
    def sslcommerz_ipn(self, **data):
        """Process the server-to-server IPN sent by SSLCOMMERZ."""
        _logger.info("Notification received from SSLCOMMERZ with data:\n%s", pprint.pformat(data))

        tx_sudo = self.env["payment.transaction"].sudo()._search_by_reference("sslcommerz", data)
        if tx_sudo:
            self._verify_and_process(data, tx_sudo=tx_sudo)
        return ""

    @staticmethod
    def _verify_and_process(data, tx_sudo):
        if not (val_id := data.get("val_id")):
            return

        try:
            verified_data = tx_sudo._send_api_request(
                "GET",
                "/validator/api/validationserverAPI.php",
                params={
                    "val_id": val_id,
                    "store_id": tx_sudo.provider_id.sslcommerz_store_id,
                    "store_passwd": tx_sudo.provider_id.sslcommerz_store_passwd,
                },
                operation="validation",
            )
        except ValidationError:
            _logger.error("Unable to process the payment data.")
        else:
            tx_sudo._record(verified_data)
