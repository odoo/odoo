# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tools import float_round

from odoo.addons.payment.tests.common import PaymentCommon


@tagged('-at_install', 'post_install')
class TestTransactions(PaymentCommon):

    def test_no_payment_for_validations(self):
        tx = self.create_transaction(flow='dummy', operation='validation')  # Overwrite the flow
        tx._reconcile_after_done()
        payment_count = self.env['account.payment'].search_count(
            [('payment_transaction_id', '=', tx.id)]
        )
        self.assertEqual(payment_count, 0, "validation transactions should not create payments")

    def test_refunds_count(self):
        tx = self.create_transaction(flow='dummy', operation='online_redirect')
        tx.acquirer_id.type_refund_supported = 'partial'
        self.create_transaction(
            flow='dummy',
            operation='refund',
            reference='Test Refund Transaction 1',
            source_transaction_id=tx.id,
            state='draft',
            amount=1.01
        )
        self.create_transaction(
            flow='dummy',
            operation='refund',
            reference='Test Refund Transaction 2',
            source_transaction_id=tx.id,
            state='draft',
            amount=10.1
        )
        self.create_transaction(
            flow='dummy',
            operation='online_redirect',
            reference='Test Not a Refund Transaction',
            source_transaction_id=tx.id,
            state='draft',
            amount=10.1
        )
        tx._compute_refunds_count()

        self.assertEqual(tx.refunds_count, 2, "There are 2 refund tx in the refunds_count.")

    def test_create_refund_transaction(self):
        tx = self.create_transaction(flow='dummy', operation='online_redirect')
        refund_tx = tx._create_refund_transaction(refund_amount=11.11)
        refund_tx_1 = tx._create_refund_transaction()
        self.assertEqual(tx.id, refund_tx.source_transaction_id.id,
                         "The `source_tx_id` of a refund should be the id of the source.")
        self.assertEqual(refund_tx.reference, "R-Test Transaction",
                         "The `reference` of a refund isn't corectly set.")
        self.assertEqual(refund_tx_1.reference, "R-Test Transaction-1",
                         "The `reference` of a refund isn't corectly set.")
        self.assertEqual(refund_tx.operation, "refund",
                         "The `operation` of a refund isn't corectly set.")
        self.assertEqual(float_round(refund_tx.amount, 2), float_round(-11.11, 2),
                         "The `amount` of a refund isn't corectly set.")
        self.assertEqual(float_round(refund_tx_1.amount, 2), float_round(-1111.11, 2),
                         "The `amount` of a refund isn't corectly set.")

    def test_create_payment_from_negative_amount_tx(self):
        tx = self.create_transaction(flow='dummy', operation='online_redirect')
        negative_amount_tx = self.create_transaction(flow='dummy', operation='online_redirect',
                                                     amount=-1111.11, reference="test negative tx")
        tx._create_payment()
        negative_amount_tx._create_payment()
        self.assertEqual(float_round(tx.payment_id.amount, 2), float_round(1111.11, 2),
                         "The `amount` of a payment must be positive.")
        self.assertEqual(float_round(negative_amount_tx.payment_id.amount, 2),
                         float_round(1111.11, 2), "The `amount` of a payment must be positive.")

    def test_get_sent_message(self):
        tx = self.create_transaction(flow='dummy', operation='online_redirect')
        refund_tx = tx._create_refund_transaction(refund_amount=11.11)
        self.assertEqual(
            tx._get_sent_message(),
            "A transaction with reference Test Transaction has been initiated (Dummy Acquirer).",
            "The sent message isn't correct."
        )
        self.assertEqual(
            refund_tx._get_sent_message(),
            "A refund request of 11.11 € has been sent. The payment will be created soon. Refund "
            "transaction reference: R-Test Transaction.",
            "The sent message isn't correct."
        )
