from openerp.addons.account.tests.account_test_users import AccountTestUsers


class AccountTestInvoices(AccountTestUsers):

    """Tests for diffrent type of user 'Accountant/Adviser' and added groups"""

    def setUp(self):
        super(AccountTestInvoices, self).setUp()
        Account = self.env['account.account']
        Invoice = self.env['account.invoice']
        payable_type = self.env.ref('account.data_account_type_payable')
        receivable_type = self.env.ref('account.data_account_type_receivable')
        expense_type = self.env.ref('account.data_account_type_expenses')
        revenue_type = self.env.ref('account.data_account_type_revenue')
        self.payment_term = self.env.ref('account.account_payment_term_advance')
        self.invoice_account_purchase = Account.search([('user_type_id', '=', payable_type.id)], limit=1)
        self.invoice_account_sales = Account.search([('user_type_id', '=', receivable_type.id)], limit=1)
        self.invoice_line_account_purchase = Account.search([('user_type_id', '=', expense_type.id)], limit=1)
        self.invoice_line_account_sales = Account.search([('user_type_id', '=', revenue_type.id)], limit=1)
        self.sales_journal = self.env['account.journal'].search([('type', '=', 'sale')])[0]
        self.purchase_journal = self.env['account.journal'].search([('type', '=', 'purchase')])[0]
        self.partner3 = self.env.ref('base.res_partner_3')
        self.invoice_line_product = self.env.ref('product.product_product_5')

        sales_invoice_line_data = [
            (0, 0, {
                'product_id': self.invoice_line_product.id,
                'quantity': 10.0,
                'account_id': self.invoice_line_account_sales.id,
                'name': 'product test 5',
                'price_unit': 100.00,
            })]

        purchase_invoice_line_data = [
            (0, 0, {
                'product_id': self.invoice_line_product.id,
                'quantity': 10.0,
                'account_id': self.invoice_line_account_purchase.id,
                'name': 'product test 5',
                'price_unit': 100.00,
            })]

        self.account_invoice_sales = Invoice.sudo(self.account_user.id).create(dict(
            name="Test Sales Invoice",
            reference_type="none",
            payment_term_id=self.payment_term.id,
            journal_id=self.sales_journal.id,
            partner_id=self.partner3.id,
            account_id=self.invoice_account_sales.id,
            invoice_line_ids=sales_invoice_line_data
        ))
        self.account_invoice_purchase = Invoice.sudo(self.account_user.id).create(dict(
            name="Test Purchase Invoice",
            reference_type="none",
            payment_term_id=self.payment_term.id,
            journal_id=self.purchase_journal.id,
            partner_id=self.partner3.id,
            account_id=self.invoice_account_purchase.id,
            invoice_line_ids=purchase_invoice_line_data
        ))
