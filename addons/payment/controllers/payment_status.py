# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import http
from odoo.exceptions import LockError
from odoo.http import request
from odoo.tools.translate import LazyTranslate

from odoo.addons.payment import utils as payment_utils

_lt = LazyTranslate(__name__)
_logger = logging.getLogger(__name__)


class PaymentStatus(http.Controller):
    """Controller for the payment status page.

    It keeps track of the transaction being monitored via the user's session and exposes routes to
    display it and trigger the immediate processing and post-processing of the transaction.
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
        # The session might have expired, or the transaction never existed.
        if monitored_tx:
            notification_access_token = payment_utils.generate_access_token(monitored_tx.id)
            notification_channel = (
                f"payment_transaction_channel:{monitored_tx.id},{notification_access_token}"
            )
            values = {"tx": monitored_tx, "notification_channel": notification_channel}
        else:
            values = {"payment_not_found": True}
        template = self.get_payment_status_template_xmlid(monitored_tx)
        return request.render(template, values)

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

    @http.route("/payment/post_process", type="jsonrpc", auth="public")
    def payment_post_process(self, **_kwargs):
        """Fetch the transaction and run its post-processing.

        :return: The post-processing values of the transaction.
        :rtype: dict
        """
        monitored_tx = self._get_monitored_transaction()
        if monitored_tx and not monitored_tx.is_post_processed:
            post_processing_cron = self.env.ref("payment.cron_post_process_payment_tx")
            try:
                post_processing_cron.lock_for_update(allow_referencing=True)
            except LockError:  # The cron is already running.
                # Schedule it to run ASAP in case it missed the current tx.
                post_processing_cron.sudo()._trigger()
            else:
                post_processing_cron.sudo().method_direct_trigger()  # Run synchronously.
                # Commit to see the updated values as cron runs in a separate cursor.
                self.env.cr.commit()

        return {
            "state": monitored_tx.state,
            "provider_code": monitored_tx.provider_code,
            "is_post_processed": monitored_tx.is_post_processed,
        }

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
