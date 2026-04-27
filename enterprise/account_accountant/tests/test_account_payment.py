from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountBillPayment(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.bank_journal_1 = cls.company_data['default_journal_bank']

    def test_bill_state_change_on_payment_state(self):
        """Test that bill payment state changes correctly when payment state transitions occur.
        • Draft payment case: Bill state reverts to 'not_paid' when payment is drafted
        • Payment unlink case: Bill state reverts to 'not_paid' when payment is deleted
        """
        bill = self.init_invoice('in_invoice', post=True, partner=self.partner_a, products=self.product_a)

        # We have to test it without any Outstanding Payment account set in Journal
        self.bank_journal_1.outbound_payment_method_line_ids.payment_account_id = False

        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=bill.ids)\
            .create({})\
            ._create_payments()
        self.assertEqual(bill.payment_state, self.env['account.move']._get_invoice_in_payment_state())

        payment.action_draft()
        self.assertEqual(payment.state, 'draft')
        self.assertEqual(payment.invoice_ids.payment_state, 'not_paid')

        payment.unlink()
        self.assertEqual(bill.payment_state, 'not_paid')
