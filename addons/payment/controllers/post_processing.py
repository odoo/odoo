# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import http
from odoo.exceptions import ConcurrencyError
from odoo.http import request
from odoo.sql_db import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY
from odoo.tools.translate import LazyTranslate

from odoo.addons.payment import utils as payment_utils

_lt = LazyTranslate(__name__)
_logger = logging.getLogger(__name__)


class PaymentPostProcessing(http.Controller):
    """
    This controller is responsible for the monitoring and finalization of the post-processing of
    transactions.

    It exposes the route `/payment/status`: All payment flows must go through this route at some
    point to allow the user checking on the transactions' status, and to trigger the finalization of
    their post-processing.
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

        :param dict _kwargs: Optional data. This parameter is not used here
        :return: The rendered status page
        :rtype: str
        """
        monitored_tx = self._get_monitored_transaction()
        # The session might have expired, or the transaction never existed.
        if monitored_tx:
            notification_access_token = payment_utils.generate_access_token([monitored_tx.id])
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

    @http.route("/payment/post_process", type="jsonrpc", auth="public")
    def payment_post_process(self, **_kwargs):
        """Fetch the transaction and trigger its post-processing.

        :return: The post-processing values of the transaction.
        :rtype: dict
        """
        # We only call the payment post-processing on existing transactions.
        monitored_tx = self._get_monitored_transaction()

        # Post-process the transaction before redirecting the user to the landing route and its
        # document.
        if not monitored_tx.is_post_processed:
            try:
                monitored_tx._post_process()
            except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY as ce:
                # Raising ConcurrencyError to trigger the framework's retrying mechanism.
                concurrency_error_message = (
                    "Post-processing failed because of a consurrency error, retrying"
                )
                raise ConcurrencyError(concurrency_error_message) from ce
            except Exception as e:
                # Error is silenced here since to avoid displaying it in the frontend for the
                # customers, in this page they are redirected after 5 seconds so no use of showing
                # the error.
                request.env.cr.rollback()
                _logger.exception(
                    "Encountered an error while post-processing transaction with id %s:\n%s",
                    monitored_tx.id,
                    e,  # noqa: TRY401
                )

        return {"state": monitored_tx.state, "provider_code": monitored_tx.provider_code}

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
            request
            .env["payment.transaction"]
            .sudo()
            .browse(request.session.get(self.MONITORED_TX_ID_KEY))
            .exists()
        )
