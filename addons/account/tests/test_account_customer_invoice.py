from odoo.addons.account.tests.account_test_users import AccountTestUsers
import datetime
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountCustomerInvoice(AccountTestUsers):

    def test_customer_invoice(self):
        # I will create bank detail with using manager access rights
        # because account manager can only create bank details.
        self.res_partner_bank_0 = self.env['res.partner.bank'].sudo(self.account_manager.id).create(dict(
            acc_type='bank',
            company_id=self.main_company.id,
            partner_id=self.main_partner.id,
            acc_number='123456789',
            bank_id=self.main_bank.id,
        ))

        # Test with that user which have rights to make Invoicing and payment and who is accountant.
        # Create a customer invoice
        self.account_invoice_obj = self.env['account.invoice']
        self.payment_term = self.env.ref('account.account_payment_term_advance')
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

        total_before_confirm = self.partner3.total_invoiced

        # I check that Initially customer invoice is in the "Draft" state
        self.assertEquals(self.account_invoice_customer0.state, 'draft')

        # I check that there is no move attached to the invoice
        self.assertEquals(len(self.account_invoice_customer0.move_id), 0)

        # I validate invoice by creating on
        self.account_invoice_customer0.action_invoice_open()

        # I check that the invoice state is "Open"
        self.assertEquals(self.account_invoice_customer0.state, 'open')

        # I check that now there is a move attached to the invoice
        assert self.account_invoice_customer0.move_id, "Move not created for open invoice"

        # I totally pay the Invoice
        self.account_invoice_customer0.pay_and_reconcile(self.env['account.journal'].search([('type', '=', 'bank')], limit=1), 10050.0)

        # I verify that invoice is now in Paid state
        assert (self.account_invoice_customer0.state == 'paid'), "Invoice is not in Paid state"

        self.partner3.invalidate_cache(ids=self.partner3.ids)
        total_after_confirm = self.partner3.total_invoiced
        self.assertEquals(total_after_confirm - total_before_confirm, self.account_invoice_customer0.amount_untaxed_signed)

        # I created a credit note Using Add Credit Note Button
        invoice_refund_obj = self.env['account.invoice.refund']
        self.account_invoice_refund_0 = invoice_refund_obj.create(dict(
            description='Credit Note for China Export',
            date=datetime.date.today(),
            filter_refund='refund'
        ))

        # I clicked on Add Credit Note button.
        self.account_invoice_refund_0.invoice_refund()
