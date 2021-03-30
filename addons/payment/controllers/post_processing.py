# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import timedelta

import psycopg2

from odoo import fields, http
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

    MONITORED_TX_IDS_KEY = '__payment_monitored_tx_ids__'

    @http.route('/payment/status', type='http', auth='public', website=True, sitemap=False)
    def display_status(self, **kwargs):
        """ Display the payment status page.

        :param dict kwargs: Optional data. This parameter is not used here
        :return: The rendered status page
        :rtype: str
        """
        return request.render('payment.payment_status')

    @http.route('/payment/status/poll', type='json', auth='public')
    def poll_status(self):
        """ Fetch the transactions to display on the status page and finalize their post-processing.

        :return: The post-processing values of the transactions
        :rtype: dict
        """
        # Retrieve recent user's transactions from the session
        limit_date = fields.Datetime.now() - timedelta(days=1)
        monitored_txs = request.env['payment.transaction'].sudo().search([
            ('id', 'in', self.get_monitored_transaction_ids()),
            ('last_state_change', '>=', limit_date)
        ])
        if not monitored_txs:  # The transaction was not correctly created
            return {
                'success': False,
                'error': 'no_tx_found',
            }

        # Build the list of display values with the display message and post-processing values
        display_values_list = []
        for tx in monitored_txs:
            display_message = None
            if tx.state == 'pending':
                display_message = tx.acquirer_id.pending_msg
            elif tx.state == 'done':
                display_message = tx.acquirer_id.done_msg
            elif tx.state == 'cancel':
                display_message = tx.acquirer_id.cancel_msg
            display_values_list.append({
                'display_message': display_message,
                **tx._get_post_processing_values(),
            })

        # Stop monitoring already post-processed transactions
        post_processed_txs = monitored_txs.filtered('is_post_processed')
        self.remove_transactions(post_processed_txs)

        # Finalize post-processing of transactions before displaying them to the user
        txs_to_post_process = (monitored_txs - post_processed_txs).filtered(
            lambda t: t.state == 'done'
        )
        success, error = True, None
        try:
            txs_to_post_process._finalize_post_processing()
        except psycopg2.OperationalError:  # A collision of accounting sequences occurred
            request.env.cr.rollback()  # Rollback and try later
            success = False
            error = 'tx_process_retry'
        except Exception as e:
            request.env.cr.rollback()
            success = False
            error = str(e)
            _logger.exception(
                "encountered an error while post-processing transactions with ids %s:\n%s",
                ', '.join([str(tx_id) for tx_id in txs_to_post_process.ids]), e
            )

        return {
            'success': success,
            'error': error,
            'display_values_list': display_values_list,
        }

    @classmethod
    def monitor_transactions(cls, transactions):
        """ Add the ids of the provided transactions to the list of monitored transaction ids.

        :param recordset transactions: The transactions to monitor, as a `payment.transaction`
                                       recordset
        :return: None
        """
        if transactions:
            monitored_tx_ids = request.session.get(cls.MONITORED_TX_IDS_KEY, [])
            request.session[cls.MONITORED_TX_IDS_KEY] = list(
                set(monitored_tx_ids).union(transactions.ids)
            )

    @classmethod
    def get_monitored_transaction_ids(cls):
        """ Return the ids of transactions being monitored.

        Only the ids and not the recordset itself is returned to allow the caller browsing the
        recordset with sudo privileges, and using the ids in a custom query.

        :return: The ids of transactions being monitored
        :rtype: list
        """
        return request.session.get(cls.MONITORED_TX_IDS_KEY, [])

    @classmethod
    def remove_transactions(cls, transactions):
        """ Remove the ids of the provided transactions from the list of monitored transaction ids.

        :param recordset transactions: The transactions to remove, as a `payment.transaction`
                                       recordset
        :return: None
        """
        if transactions:
            monitored_tx_ids = request.session.get(cls.MONITORED_TX_IDS_KEY, [])
            request.session[cls.MONITORED_TX_IDS_KEY] = [
                tx_id for tx_id in monitored_tx_ids if tx_id not in transactions.ids
            ]
