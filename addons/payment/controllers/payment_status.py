# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import http
from odoo.http import request
from odoo.tools.translate import LazyTranslate

from odoo.addons.payment import utils as payment_utils

_lt = LazyTranslate(__name__)
_logger = logging.getLogger(__name__)


class PaymentStatus(http.Controller):
    """Controller for the payment status page.

    It keeps track of the transaction being monitored via the user's session and exposes routes to
    display it and trigger its immediate processing.
    """

    MONITORED_TX_ID_KEY = "__payment_monitored_tx_id__"

    @http.route(
        "/payment/status",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        list_as_website_content=_lt("Payment Status"),
    )
    def display_status(self, **_kwargs):
        """Fetch the transaction and display it on the payment status page.

        All payment flows that go through the payment form land on this route.

        :param dict _kwargs: Optional data. This parameter is not used here
        :return: The rendered status page
        :rtype: str
        """
        monitored_tx = self._get_monitored_transaction()
        values = self._get_payment_status_values(monitored_tx)
        template = self.get_payment_status_template_xmlid(monitored_tx)
        return request.render(template, values)

    def _get_payment_status_values(self, tx):
        """Return the QWeb rendering values for the payment status page.

        Meant to be overridden to add document-specific values to the page.

        :param payment.transaction tx: The monitored transaction, if any.
        :return: The rendering values.
        :rtype: dict
        """
        # The session might have expired, or the transaction never existed.
        if not tx:
            return {"payment_not_found": True}
        notification_access_token = payment_utils.generate_access_token(tx.id)
        notification_channel = (
            f"payment_transaction_channel:{tx.id},{notification_access_token}"
        )
        return {
            "tx": tx,
            "notification_channel": notification_channel,
            "extra_session_info": {"bus_info": request.env["ir.http"]._get_bus_session_info()},
        }

    def get_payment_status_template_xmlid(self, tx):  # noqa: ARG002
        return "payment.payment_status"

    @http.route("/payment/process", type="jsonrpc", auth="public")
    def payment_process(self):
        """Run the processing of the current transaction.

        :rtype: None
        """
        monitored_tx_sudo = self._get_monitored_transaction()
        if not monitored_tx_sudo.payment_data_ids:  # The transaction has already been processed
            return

        self.env["payment.transaction"]._run_processing()

    @classmethod
    def monitor_transaction(cls, transaction):
        """Make the provided transaction id monitored.

        :param payment.transaction transaction: The transaction to monitor.
        :return: None
        """
        request.session[cls.MONITORED_TX_ID_KEY] = transaction.id

    def _get_monitored_transaction(self):
        """Retrieve the user's last transaction from the session (the transaction being monitored).

        :return: the user's last transaction
        :rtype: payment.transaction
        """
        return (
            self
            .env["payment.transaction"]
            .sudo()
            .browse(request.session.get(self.MONITORED_TX_ID_KEY))
            .exists()
        )
