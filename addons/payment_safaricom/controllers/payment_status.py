# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers.payment_status import PaymentStatus
from odoo.addons.payment_safaricom import const


class SafaricomPaymentStatus(PaymentStatus):
    @http.route(const.PAY_URL, type="http", auth="public", website=True, sitemap=False)
    def safaricom_display_pay_page(self, **_kwargs):
        """Display the waiting page of the monitored transaction's STK Push prompt.

        The page waits for the webhook's callback-received bus notification (or a 2-minute
        timeout, the lifespan of an STK Push prompt) and exits to `/payment/status`, whose
        processing call finalizes the transaction synchronously.

        :return: The rendered waiting page, or a redirection to the status page
        :rtype: str
        """
        tx_sudo = self._get_monitored_transaction()
        if (
            not tx_sudo
            or tx_sudo.provider_code != "safaricom"
            or tx_sudo.state not in ("draft", "pending")
        ):
            return request.redirect("/payment/status")

        access_token = payment_utils.generate_access_token(tx_sudo.id)
        return request.render(
            "payment_safaricom.pay_page",
            {
                "tx": tx_sudo,
                "notification_channel": f"payment_transaction_channel:{tx_sudo.id},{access_token}",
            },
        )

    @http.route(const.CANCEL_URL, type="jsonrpc", auth="public")
    def safaricom_cancel_payment(self):
        """Cancel the monitored transaction at the customer's request."""
        tx_sudo = self._get_monitored_transaction()
        if not tx_sudo or tx_sudo.provider_code != "safaricom":
            raise Forbidden(self.env._("Invalid Transaction"))

        if tx_sudo.state in ("draft", "pending"):
            tx_sudo._record({"canceled_by_customer": True})
