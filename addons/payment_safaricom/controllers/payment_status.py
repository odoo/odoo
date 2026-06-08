# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden

from odoo import http

from odoo.addons.payment.controllers.payment_status import PaymentStatus
from odoo.addons.payment_safaricom import const


class SafaricomPaymentStatus(PaymentStatus):
    def get_payment_status_template_xmlid(self, tx):
        if tx and tx.provider_code == "safaricom":
            return "payment_safaricom.payment_status"
        return super().get_payment_status_template_xmlid(tx)

    @http.route(const.CANCEL_URL, type="jsonrpc", auth="public")
    def safaricom_cancel_payment(self):
        """Cancel the monitored transaction at the customer's request."""
        tx_sudo = self._get_monitored_transaction()
        if not tx_sudo or tx_sudo.provider_code != "safaricom":
            raise Forbidden(self.env._("Invalid Transaction"))

        if tx_sudo.state in ("draft", "pending"):
            tx_sudo._record({"canceled_by_customer": True})
            self.env["payment.transaction"]._run_processing()
