from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nTRSalesReturnAccount(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('tr')
    def setUpClass(cls):
        super().setUpClass()

        cls.invoice = cls._create_invoice_one_line(product_id=cls.product_a, price_unit=1000.0, post=True)
        cls.sales_account = cls.invoice.invoice_line_ids.account_id
        cls.return_account = cls.invoice.journal_id.l10n_tr_default_sales_return_account_id

    def test_credit_note_uses_the_journal_return_account(self):
        self.assertTrue(self.return_account, "The Turkish sales journal should default to a return account.")
        self.assertNotEqual(
            self.sales_account, self.return_account,
            "Sales and sales returns are kept on separate accounts, otherwise this test proves nothing.",
        )

        credit_note = self._reverse_invoice(self.invoice)

        self.assertRecordValues(credit_note.invoice_line_ids, [{'account_id': self.return_account.id}])

    def test_cancelling_reversal_keeps_the_sales_account(self):
        reversal = self.invoice._reverse_moves(cancel=True)

        self.assertRecordValues(reversal.invoice_line_ids, [{'account_id': self.sales_account.id}])

    def test_duplicated_invoice_keeps_the_sales_account(self):
        self.assertRecordValues(self.invoice.copy().invoice_line_ids, [{'account_id': self.sales_account.id}])
