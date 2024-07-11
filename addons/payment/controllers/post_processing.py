# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import psycopg2

from odoo import http
from odoo.http import request

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

    @http.route('/payment/status', type='http', auth='public', website=True, sitemap=False)
    def display_status(self, **kwargs):
        """ Display the payment status page.

        :param dict kwargs: Optional data. This parameter is not used here
        :return: The rendered status page
        :rtype: str
        """
        return request.render('payment.payment_status')

    @http.route('/payment/status/poll', type='json', auth='public')
    def poll_status(self, **_kwargs):
        """ Fetch the transaction to display on the status page and finalize its post-processing.

        :return: The post-processing values of the transaction.
        :rtype: dict
        """
        # Retrieve the last user's transaction from the session.
        monitored_tx = request.env['payment.transaction'].sudo().browse(
            self.get_monitored_transaction_id()
        ).exists()
        if not monitored_tx:  # The session might have expired, or the tx has never existed.
            raise Exception('tx_not_found')

        # Finalize the post-processing of the transaction before redirecting the user to the landing
        # route and its document.
        if monitored_tx.state == 'done' and not monitored_tx.is_post_processed:
            try:
                monitored_tx._finalize_post_processing()
            except psycopg2.OperationalError:  # The database cursor could not be committed.
                request.env.cr.rollback()  # Rollback and try later.
                raise Exception('retry')
            except Exception as e:
                request.env.cr.rollback()
                _logger.exception(
                    "Encountered an error while post-processing transaction with id %s:\n%s",
                    monitored_tx.id, e
                )
                raise

        # Return the post-processing values to display the transaction summary to the customer.
        return monitored_tx._get_post_processing_values()

    @classmethod
    def monitor_transaction(cls, transaction):
        """ Make the provided transaction id monitored.

        :param payment.transaction transaction: The transaction to monitor.
        :return: None
        """
        request.session[cls.MONITORED_TX_ID_KEY] = transaction.id

    @classmethod
    def get_monitored_transaction_id(cls):
        """ Return the id of transaction being monitored.

        Only the id and not the recordset itself is returned to allow the caller browsing the
        recordset with sudo privileges, and using the id in a custom query.

        :return: The id of transactions being monitored
        :rtype: list
        """
        return request.session.get(cls.MONITORED_TX_ID_KEY)
