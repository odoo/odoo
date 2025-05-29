# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import psycopg2

from odoo import http
from odoo.http import request
from odoo.tools.translate import LazyTranslate

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

    MONITORED_TX_ID_KEY = '__payment_monitored_tx_id__'

    @http.route('/payment/status', type='http', auth='public', website=True, sitemap=False, list_as_website_content=_lt("Payment Status"))
    def display_status(self, **kwargs):
        """ Fetch the transaction and display it on the payment status page.

        :param dict kwargs: Optional data. This parameter is not used here
        :return: The rendered status page
        :rtype: str
        """
        monitored_tx = self._get_monitored_transaction()
        # The session might have expired, or the transaction never existed.
        values = {'tx': monitored_tx} if monitored_tx else {'payment_not_found': True}
        return request.render('payment.payment_status', values)

    @http.route('/payment/status/poll', type='jsonrpc', auth='public')
    def poll_status(self, **_kwargs):
        """ Fetch the transaction and trigger its post-processing.

        :return: The post-processing values of the transaction.
        :rtype: dict
        """
        # We only poll the payment status if a payment was found, so the transaction should exist.
        monitored_tx = self._get_monitored_transaction()

        # Post-process the transaction before redirecting the user to the landing route and its
        # document.
        if not monitored_tx.is_post_processed:
            try:
                monitored_tx._post_process()
            except (
                psycopg2.OperationalError, psycopg2.IntegrityError
            ):  # The database cursor could not be committed.
                request.env.cr.rollback()  # Rollback and try later.
                raise Exception('retry')
            except Exception as e:
                request.env.cr.rollback()
                _logger.exception(
                    "Encountered an error while post-processing transaction with id %s:\n%s",
                    monitored_tx.id, e
                )
                raise

        return {
            'provider_code': monitored_tx.provider_code,
            'state': monitored_tx.state,
            'landing_route': monitored_tx.landing_route,
        }

    @classmethod
    def monitor_transaction(cls, transaction):
        """ Make the provided transaction id monitored.

        :param payment.transaction transaction: The transaction to monitor.
        :return: None
        """
        request.session[cls.MONITORED_TX_ID_KEY] = transaction.id

    def _get_monitored_transaction(self):
        """ Retrieve the user's last transaction from the session (the transaction being monitored).

        :return: the user's last transaction
        :rtype: payment.transaction
        """
        return request.env['payment.transaction'].sudo().browse(
            request.session.get(self.MONITORED_TX_ID_KEY)
        ).exists()
