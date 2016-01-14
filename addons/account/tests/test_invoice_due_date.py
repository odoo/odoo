from openerp.addons.account.tests.account_test_users import AccountTestUsers
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
import datetime


class TestAccountCustomerInvoiceDueDate(AccountTestUsers):
    def setUp(self):
        super(TestAccountCustomerInvoiceDueDate, self).setUp()
        self.payment_term_model = self.env['account.payment.term']

        payment_term_vals = {
                             'name': '30 days end month on 10',
                             'line_ids': [(0,0, {'days': 0,
                                                 'option': 'last_day_following_month',
                                                 'sequence': 20,
                                                 'value': 'fixed',
                                                 'value_amount': 0}),
                                          (0,0, {'days': 10,
                                                 'option': 'fix_day_following_month',
                                                 'sequence': 30,
                                                 'value': 'balance',
                                                 'value_amount': 0}),
                                          ]
                             }
        self.payment_term_30_days_end_month_on_10 = self.payment_term_model.sudo(
            self.account_manager.id).create(payment_term_vals)

    def test_customer_invoice_due_date(self):
        # Test with that user which have rights to make Invoicing and who is accountant.
        # Create a customer invoice
        self.account_invoice_obj = self.env['account.invoice']
        self.payment_term = self.payment_term_30_days_end_month_on_10
        self.journalrec = self.env['account.journal'].search([('type', '=', 'sale')])[0]
        self.partner3 = self.env.ref('base.res_partner_3')
        account_user_type = self.env.ref('account.data_account_type_receivable')
        self.ova = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_current_assets').id)], limit=1)

        #only adviser can create an account
        self.account_rec1_id = self.account_model.sudo(self.account_manager.id).create(dict(
            code="cust_acc",
            name="customer account",
            user_type_id=account_user_type.id,
            reconcile=True,
        ))

        invoice_line_data = [
            (0, 0,
                {
                    'product_id': self.env.ref('product.product_product_5').id,
                    'quantity': 10.0,
                    'account_id': self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1).id,
                    'name': 'product test 5',
                    'price_unit': 100.00,
                }
             )
        ]

        self.account_invoice_customer0 = self.account_invoice_obj.sudo(self.account_user.id).create(dict(
            name="Test Customer Invoice",
            reference_type="none",
            payment_term_id=self.payment_term.id,
            journal_id=self.journalrec.id,
            partner_id=self.partner3.id,
            account_id=self.account_rec1_id.id,
            invoice_line_ids=invoice_line_data
        ))

        # I manually assign tax on invoice
        invoice_tax_line = {
            'name': 'Test Tax for Customer Invoice',
            'manual': 1,
            'amount': 9050,
            'account_id': self.ova.id,
            'invoice_id': self.account_invoice_customer0.id,
        }
        tax = self.env['account.invoice.tax'].create(invoice_tax_line)
        assert tax, "Tax has not been assigned correctly"

        # I check that Initially customer invoice is in the "Draft" state
        self.assertEquals(self.account_invoice_customer0.state, 'draft')

        # I validate invoice by creating on
        self.account_invoice_customer0.signal_workflow('invoice_open')

        # I check that the invoice state is "Open"
        self.assertEquals(self.account_invoice_customer0.state, 'open')

        date_invoice = self.account_invoice_customer0.date_invoice
        expected_due_date = datetime.datetime.strptime(date_invoice, DEFAULT_SERVER_DATE_FORMAT)
        expected_due_date += relativedelta(day=31, months=1)
        expected_due_date += relativedelta(day=1, months=1)  # Getting 1st of next month
        expected_due_date += relativedelta(days=10 - 1)

        expected_due_date_str = expected_due_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
        print expected_due_date_str
        self.assertEquals(expected_due_date_str, self.account_invoice_customer0.date_due)
