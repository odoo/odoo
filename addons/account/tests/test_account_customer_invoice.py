from openerp.addons.account.tests.account_test_users import AccountTestUsers


class TestAccountCustomerInvoive(AccountTestUsers):

    def test_customer_invoice(self):
        # I will create bank detail with using manager access rights
        # because account manager can only create bank details.
        self.res_partner_bank_0 = self.env['res.partner.bank'].sudo(self.account_manager).create(dict(
            state="bank",
            company_id=self.main_company.id,
            partner_id=self.main_partner.id,
            acc_number="123456789",
            footer=True,
            bank=self.main_bank.id,
            bank_name="Reserve"
        ))

        # Test with that user which have rights to make Invoicing and payment and who is accountant.
        # Create a customer invoice
        self.account_invice_obj = self.env['account.invoice']
        self.account_object = self.env['account.account']
        self.payment_term_id = self.env.ref('account.account_payment_term_advance')
        self.journalrec_id = self.env.ref('account.sales_journal')
        self.partner3_id = self.env.ref('base.res_partner_3')
        account_user_type = self.env.ref('account.data_account_type_cash')

        self.account_rec1_id = self.account_object.sudo(self.account_user).create(dict(
            code="cust_acc",
            name="customer account",
            user_type=account_user_type.id
        ))

        invoice_line_data = [
            (0, 0,
                {
                    'product_id': self.ref('product.product_product_5'),
                    'quantity': 10.0,
                    'account_id': self.ref('account.a_sale'),
                    'name': 'product test 5',
                    'price_unit': 100.00,
                }
        )]

        self.account_invoice_customer0 = self.account_invice_obj.sudo(self.account_user).create(dict(
            name="Test Customer Invoice",
            reference_type="none",
            partner_bank_id=self.res_partner_bank_0.id,
            payment_term=self.payment_term_id.id,
            journal_id=self.journalrec_id.id,
            partner_id=self.partner3_id.id,
            account_id=self.account_rec1_id.id,
            invoice_line=invoice_line_data
        ))
