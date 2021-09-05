# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

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
