from openerp.addons.account.tests.account_test_classes import AccountingTestCase
import time

class TestCheckWriting(AccountingTestCase):

    def setUp(self):
        super(TestCheckWriting, self).setUp()
        self.invoice_model = self.env['account.invoice']
        self.invoice_line_model = self.env['account.invoice.line']
        self.register_payments_model = self.env['account.register.payments']

        self.partner_axelor = self.env.ref("base.res_partner_13")
        self.product = self.env.ref("product.product_product_4")
        self.payment_method_check = self.env.ref("account_check_writing.account_payment_method_check_writing")

        self.account_payable = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_payable').id)], limit=1)
        self.account_expenses = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_expenses').id)], limit=1)

        self.bank = self.env['res.partner.bank'].create({'acc_number': '0123456789', 'bank_name': 'Test Bank', 'company_id': self.env.user.company_id.id})
        self.bank_journal = self.bank.journal_id

    def create_invoice(self, amount=100, is_refund=False):
        invoice = self.invoice_model.create({
            'partner_id': self.partner_axelor.id,
            'reference_type': 'none',
            'name': is_refund and "Supplier Refund" or "Supplier Invoice",
            'type': is_refund and "in_refund" or "in_invoice",
            'account_id': self.account_payable.id,
            'date_invoice': time.strftime('%Y') + '-06-26',
        })
        self.invoice_line_model.create({
            'product_id': self.product.id,
            'quantity': 1,
            'price_unit': is_refund and amount/4 or amount,
            'invoice_id': invoice.id,
            'name': 'something',
            'account_id': self.account_expenses.id,
        })
        invoice.signal_workflow('invoice_open')
        return invoice

    def create_payment(self, invoices):
        register_payments = self.register_payments_model.with_context({
            'active_model': 'account.invoice',
            'active_ids': invoices.ids
        }).create({
            'payment_date': time.strftime('%Y') + '-07-15',
            'journal_id': self.bank_journal.id,
            'payment_method_id': self.payment_method_check.id,
        })
        register_payments.create_payment()
        return self.env['account.payment'].search([], order="id desc", limit=1)

    def test_send_check(self):
        # Create a payment and 'send' the check
        payment = self.create_payment(self.create_invoice())
        payment.send_checks()
        self.assertEqual(payment.state, 'sent')
