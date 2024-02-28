# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment_authorize.tests.common import AuthorizeCommon


@tagged('post_install', '-at_install')
class TestRefundFlows(AuthorizeCommon):

    def test_refunding_voided_tx_cancels_it(self):
        """ Test that refunding a transaction that has been voided from Authorize.net side cancels
        it on Odoo. """
        source_tx = self._create_transaction('direct', state='done')
        with patch(
            'odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI'
            '.get_transaction_details',
            return_value={'transaction': {'transactionStatus': 'voided'}},
        ):
            source_tx._send_refund_request(amount_to_refund=source_tx.amount)
        self.assertEqual(source_tx.state, 'cancel')

    def test_refunding_refunded_tx_creates_refund_tx(self):
        """ Test that refunding a transaction that has been refunded from Authorize.net side creates
        a refund transaction on Odoo. """
        source_tx = self._create_transaction('direct', state='done')
        with patch(
            'odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI'
            '.get_transaction_details',
            return_value={'transaction': {'transactionStatus': 'refundSettledSuccessfully'}},
        ):
            source_tx._send_refund_request(amount_to_refund=source_tx.amount)
        refund_tx = self.env['payment.transaction'].search(
            [('source_transaction_id', '=', source_tx.id)]
        )
        self.assertTrue(refund_tx)

    @mute_logger('odoo.addons.payment_authorize.models.payment_transaction')
    def test_refunding_authorized_tx_voids_it(self):
        """ Test that refunding a transaction that is still authorized on Authorize.net side voids
        it instead. """
        source_tx = self._create_transaction('direct', state='done')
        with patch(
            'odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI'
            '.get_transaction_details',
            return_value={'transaction': {'transactionStatus': 'authorizedPendingCapture'}},
        ), patch(
            'odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI.void'
        ) as void_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ):
            source_tx._send_refund_request(amount_to_refund=source_tx.amount)
        self.assertEqual(void_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_authorize.models.payment_transaction')
    def test_refunding_captured_tx_refunds_it_and_creates_refund_tx(self):
        """ Test that refunding a transaction that is captured on Authorize.net side captures it and
        create a refund transaction on Odoo. """
        source_tx = self._create_transaction('direct', state='done')
        with patch(
            'odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI'
            '.get_transaction_details',
            return_value={'transaction': {'transactionStatus': 'settledSuccessfully'}},
        ), patch(
            'odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI.refund'
        ) as refund_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ):
            source_tx._send_refund_request(amount_to_refund=source_tx.amount)
        self.assertEqual(refund_mock.call_count, 1)
        refund_tx = self.env['payment.transaction'].search(
            [('source_transaction_id', '=', source_tx.id)]
        )
        self.assertTrue(refund_tx)
