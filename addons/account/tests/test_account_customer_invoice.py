from openerp.addons.account.tests.account_test_users import AccountTestUsers
import datetime


class TestAccountCustomerInvoive(AccountTestUsers):

    def test_customer_invoice(self):
        # I will create bank detail with using manager access rights
        # because account manager can only create bank details.
        self.res_partner_bank_0 = self.env['res.partner.bank'].sudo(self.account_manager.id).create(dict(
            state='bank',
            company_id=self.main_company.id,
            partner_id=self.main_partner.id,
            acc_number='123456789',
            footer=True,
            bank=self.main_bank.id,
            bank_name=self.main_bank.name,
        ))

        # Test with that user which have rights to make Invoicing and payment and who is accountant.
        # Create a customer invoice
        self.account_invice_obj = self.env['account.invoice']
        self.payment_term = self.env.ref('account.account_payment_term_advance')
        self.journalrec = self.env.ref('account.sales_journal')
        self.partner3 = self.env.ref('base.res_partner_3')
        account_user_type = self.env.ref('account.data_account_type_cash')

        self.account_rec1_id = self.account_model.sudo(self.account_user.id).create(dict(
            code="cust_acc",
            name="customer account",
            user_type=account_user_type.id,
            reconcile=True,
        ))

        invoice_line_data = [
            (0, 0,
                {
                    'product_id': self.env.ref('product.product_product_5').id,
                    'quantity': 10.0,
                    'account_id': self.env.ref('account.a_sale').id,
                    'name': 'product test 5',
                    'price_unit': 100.00,
                }
             )
        ]

        self.account_invoice_customer0 = self.account_invice_obj.sudo(self.account_user.id).create(dict(
            name="Test Customer Invoice",
            reference_type="none",
            # partner_bank_id=self.res_partner_bank_0.id,
            payment_term=self.payment_term.id,
            journal_id=self.journalrec.id,
            partner_id=self.partner3.id,
            account_id=self.account_rec1_id.id,
            invoice_line=invoice_line_data
        ))

        # I manually assign tax on invoice
        self.invoice_tax_obj = self.env['account.invoice.tax']
        amt = self.invoice_tax_obj.amount_change(50.0, self.env.ref('base.EUR').id, self.env.ref('base.main_company').id, False)
        base_amt = self.invoice_tax_obj.base_change(9000.0, self.env.ref('base.EUR').id, self.env.ref('base.main_company').id, False)
        invoice_tax_line = {
            'name':  'Test Tax for Customer Invoice',
            'manual': 1,
            'base': base_amt['value']['base_amount'],
            'amount': amt['value']['tax_amount'],
            'account_id': self.env.ref('account.ova').id,
            'invoice_id': self.account_invoice_customer0.id,
        }
        tax = self.invoice_tax_obj.create(invoice_tax_line)
        assert tax, "Tax has not been assigned correctly"

        # I check that Initially customer invoice is in the "Draft" state
        self.assertEquals(self.account_invoice_customer0.state, 'draft')

        # I change the state of invoice to "Proforma2" by clicking PRO-FORMA button
        self.account_invoice_customer0.signal_workflow('invoice_proforma2')

        # I check that the invoice state is now "Proforma2"
        self.assertEquals(self.account_invoice_customer0.state, 'proforma2')

        # I check that there is no move attached to the invoice
        self.assertEquals(len(self.account_invoice_customer0.move_id), 0)

        # I create invoice by clicking on Create button
        self.account_invoice_customer0.signal_workflow('invoice_open')

        # I check that the invoice state is "Open"
        self.assertEquals(self.account_invoice_customer0.state, 'open')

        # I check that now there is a move attached to the invoice
        assert self.account_invoice_customer0.move_id, "Move not created for open invoice"

        # I pay the Invoice
        pay = self.account_invoice_customer0.pay_and_reconcile(
            9050.0, self.env.ref('account.cash').id,
            datetime.date.today(), self.env.ref('account.bank_journal').id,
            self.env.ref('account.cash').id,
            self.env.ref('account.bank_journal').id,
        )
        assert pay, "Incorrect Payment"

        # I verify that invoice is now in Paid state
        assert (self.account_invoice_customer0.state == 'paid'), "Invoice is not in Paid state"

        # I refund the invoice Using Refund Button
        invoice_refund_obj = self.env['account.invoice.refund']
        self.account_invoice_refund_0 = invoice_refund_obj.create(dict(
            description='Refund To China Export',
            date=datetime.date.today(),
            filter_refund='refund'
        ))

        # I clicked on refund button.
        self.account_invoice_refund_0.invoice_refund()
