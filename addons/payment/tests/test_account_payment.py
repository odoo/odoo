# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tools import float_round

from odoo.addons.payment.tests.common import PaymentCommon


@tagged('-at_install', 'post_install')
class TestAccountPayment(PaymentCommon):

    def test_available_amount_for_refund_not_supported(self):
        tx_no_refund = self.create_transaction(flow='dummy', operation='online_redirect')
        tx_no_refund._reconcile_after_done()
        self.assertEqual(
            tx_no_refund.payment_id.available_amount_for_refund,
            0,
            "The payment's `available_amount_for_refund` with an acquirer who don't support refund "
            "should be 0."
        )

    def test_available_amount_for_refund_only_full_supported(self):
        tx_full_refund_available = self.create_transaction(flow='dummy', operation='online_redirect')
        tx_full_refund_available.acquirer_id.type_refund_supported = 'full'
        tx_full_refund_available._reconcile_after_done()

        tx_fully_refunded = self.create_transaction(flow='dummy', operation='online_redirect',
                                                    reference='Test with Refund')
        tx_fully_refunded.acquirer_id.type_refund_supported = 'full'
        tx_fully_refunded._reconcile_after_done()
        refund_tx = self.create_transaction(
            flow='dummy',
            operation='refund',
            reference='Test Refund Transaction',
            source_transaction_id=tx_fully_refunded.id,
            state='draft'
        )
        refund_tx.payment_id._compute_available_amount_for_refund()

        self.assertEqual(
            float_round(tx_full_refund_available.payment_id.available_amount_for_refund, 2),
            float_round(tx_full_refund_available.amount, 2),
            "The payment's `available_amount_for_refund` with an acquirer who support refund before"
            " the transaction being refunded should be the transaction's amount"
        )
        self.assertEqual(
            tx_fully_refunded.payment_id.available_amount_for_refund,
            0,
            "The payment's `available_amount_for_refund` with an acquirer who support only full "
            "refund after the transaction has been refund should be 0."
        )

    def test_available_amount_for_refund_partially_supported(self):
        tx_part_refund_available = self.create_transaction(flow='dummy', operation='online_redirect')
        tx_part_refund_available.acquirer_id.type_refund_supported = 'partial'
        tx_part_refund_available._reconcile_after_done()

        tx_partially_refunded = self.create_transaction(flow='dummy', operation='online_redirect',
                                                        reference='Test with Refund')
        tx_partially_refunded.acquirer_id.type_refund_supported = 'partial'
        tx_partially_refunded._reconcile_after_done()
        refund_tx_1 = self.create_transaction(
            flow='dummy',
            operation='refund',
            reference='Test Refund Transaction 1',
            source_transaction_id=tx_partially_refunded.id,
            state='draft',
            amount=1.01
        )
        refund_tx_2 = self.create_transaction(
            flow='dummy',
            operation='refund',
            reference='Test Refund Transaction 2',
            source_transaction_id=tx_partially_refunded.id,
            state='draft',
            amount=10.1
        )
        tx_partially_refunded.payment_id._compute_available_amount_for_refund()

        self.assertEqual(
            float_round(tx_part_refund_available.payment_id.available_amount_for_refund, 2),
            float_round(tx_part_refund_available.amount, 2),
            "The payment's `available_amount_for_refund` with an acquirer who support refund before"
            " the transaction being refunded should be the transaction's amount."
        )
        self.assertEqual(
            tx_partially_refunded.payment_id.available_amount_for_refund,
            tx_partially_refunded.amount - refund_tx_1.amount - refund_tx_2.amount,
            "The payment's `available_amount_for_refund` with an acquirer who support partial "
            "refund after a partial transaction should be the original amount - the refunded amount"
        )

    def test_refunds_count(self):
        tx = self.create_transaction(flow='dummy', operation='online_redirect')
        tx.acquirer_id.type_refund_supported = 'partial'
        tx._reconcile_after_done()
        refund_tx_1 = self.create_transaction(
            flow='dummy',
            operation='refund',
            reference='Test Refund Transaction 1',
            source_transaction_id=tx.id,
            state='draft',
            amount=1.01
        )
        refund_tx_2 = self.create_transaction(
            flow='dummy',
            operation='refund',
            reference='Test Refund Transaction 2',
            source_transaction_id=tx.id,
            state='draft',
            amount=10.1
        )
        not_refund_tx = self.create_transaction(
            flow='dummy',
            operation='online_redirect',
            reference='Test Not a Refund Transaction',
            source_transaction_id=tx.id,
            state='draft',
            amount=10.1
        )
        refund_tx_1._reconcile_after_done()
        refund_tx_2._reconcile_after_done()
        not_refund_tx._reconcile_after_done()
        tx.payment_id._compute_refunds_count()

        self.assertEqual(
            tx.payment_id.refunds_count,
            2,
            "There are 2 refunds transactions in the refunds_count."
        )
