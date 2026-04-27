# -*- encoding: utf-8 -*-

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo import fields, Command
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestBillsPrediction(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company.predict_bill_product = True

        cls.test_partners = cls.env['res.partner'].create([{'name': 'test partner %s' % i} for i in range(7)])

        accounts_data = [{
            'code': 'test%s' % i,
            'name': name,
            'account_type': 'expense',
        } for i, name in enumerate((
            "Test Maintenance and Repair",
            "Test Purchase of services, studies and preparatory work",
            "Test Various Contributions",
            "Test Rental Charges",
            "Test Purchase of commodity",
        ))]

        cls.test_accounts = cls.env['account.account'].create(accounts_data)

        cls.frozen_today = fields.Date.today()

    def _create_bill(self, vendor, line_name, expected_account, account_to_set=None, post=True):
        ''' Create a new vendor bill to test the prediction.
        :param vendor:              The vendor to set on the invoice.
        :param line_name:           The name of the invoice line that will be used to predict.
        :param expected_account:    The expected predicted account.
        :param account_to_set:      The optional account to set as a correction of the predicted account.
        :return:                    The newly created vendor bill.
        '''
        invoice_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        invoice_form.partner_id = vendor
        invoice_form.invoice_date = self.frozen_today
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            # Set the default account to avoid "account_id is a required field" in case of bad configuration.
            invoice_line_form.account_id = self.company_data['default_journal_purchase'].default_account_id

            invoice_line_form.quantity = 1.0
            invoice_line_form.price_unit = 42.0
            invoice_line_form.name = line_name
        invoice = invoice_form.save()
        invoice_line = invoice.invoice_line_ids

        self.assertEqual(
            invoice_line.account_id,
            expected_account,
            "Account '%s' should have been predicted instead of '%s'" % (
                expected_account.display_name,
                invoice_line.account_id.display_name,
            ),
        )

        if account_to_set:
            invoice_line.account_id = account_to_set

        if post:
            invoice.action_post()
        return invoice

    def test_account_prediction_flow(self):
        default_account = self.company_data['default_journal_purchase'].default_account_id
        self._create_bill(self.test_partners[0], "Maintenance and repair", self.test_accounts[0])
        self._create_bill(self.test_partners[5], "Subsidies obtained", default_account, account_to_set=self.test_accounts[1])
        self._create_bill(self.test_partners[6], "Prepare subsidies file", default_account, account_to_set=self.test_accounts[1])
        self._create_bill(self.test_partners[6], "Prepare subsidies file", self.test_accounts[1])
        self._create_bill(self.test_partners[1], "Contributions January", self.test_accounts[2])
        self._create_bill(self.test_partners[2], "Coca-cola", default_account, account_to_set=self.test_accounts[4])
        self._create_bill(self.test_partners[1], "Contribution February", self.test_accounts[2])
        self._create_bill(self.test_partners[3], "Electricity Bruxelles", default_account, account_to_set=self.test_accounts[3])
        self._create_bill(self.test_partners[3], "Electricity Grand-Rosière", self.test_accounts[3])
        self._create_bill(self.test_partners[2], "Purchase of coca-cola", self.test_accounts[4])
        self._create_bill(self.test_partners[4], "Crate of coca-cola", default_account, account_to_set=self.test_accounts[4])
        self._create_bill(self.test_partners[4], "Crate of coca-cola", self.test_accounts[4])
        self._create_bill(self.test_partners[1], "March", self.test_accounts[2])

    def test_account_prediction_from_label_expected_behavior(self):
        """Prevent the prediction from being annoying."""
        default_account = self.company_data['default_journal_purchase'].default_account_id
        payable_account = self.company_data['default_account_payable'].copy()
        payable_account.write({'name': f'Account payable - {self.test_accounts[0].name}'})

        # There is no prior result, we take the default account, but we don't post
        self._create_bill(self.test_partners[0], self.test_partners[0].name, default_account, post=False)

        # There is no prior result, we take the default account
        self._create_bill(self.test_partners[0], "Drinks", default_account, account_to_set=self.test_accounts[0])

        # There is only one prior account for the partner, we take that one
        self._create_bill(self.test_partners[0], "Desert", self.test_accounts[0], account_to_set=self.test_accounts[1])

        # We find something close enough, take that one
        self._create_bill(self.test_partners[0], "Drinks too", self.test_accounts[0])

        # There is no clear preference for any account (both previous accounts have the same rank)
        # don't make any prediction and let the default behavior fill the account
        invoice = self._create_bill(self.test_partners[0], "Main course", default_account)
        invoice.button_draft()

        with Form(invoice) as move_form:
            with move_form.invoice_line_ids.edit(0) as line_form:
                # There isn't any account clearly better than the manually set one, we keep the current one
                line_form.account_id = self.test_accounts[2]
                line_form.name = "Apple"
                self.assertEqual(line_form.account_id, self.test_accounts[2])

                # There is an account that looks clearly better, use it
                line_form.name = "Second desert"
                self.assertEqual(line_form.account_id, self.test_accounts[1])

    def test_account_prediction_with_product(self):
        product = self.env['product.product'].create({
            'name': 'product_a',
            'lst_price': 1000.0,
            'standard_price': 800.0,
            'property_account_income_id': self.company_data['default_account_revenue'].id,
            'property_account_expense_id': self.company_data['default_account_expense'].id,
        })

        invoice_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        invoice_form.partner_id = self.test_partners[0]
        invoice_form.invoice_date = self.frozen_today
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.product_id = product
            invoice_line_form.name = "Maintenance and repair"
        invoice = invoice_form.save()

        self.assertRecordValues(invoice.invoice_line_ids, [{
            'name': "Maintenance and repair",
            'product_id': product.id,
            'account_id': self.company_data['default_account_expense'].id,
        }])

    def test_product_prediction_price_subtotal_computation(self):
        invoice_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        invoice_form.partner_id = self.test_partners[0]
        invoice_form.invoice_date = self.frozen_today
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.product_id = self.product_a
        invoice = invoice_form.save()
        invoice.action_post()

        self.product_a.supplier_taxes_id = [Command.set(self.tax_purchase_b.ids)]

        invoice_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        invoice_form.partner_id = self.test_partners[0]
        invoice_form.invoice_date = self.frozen_today
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'product_a'
        invoice = invoice_form.save()

        self.assertRecordValues(invoice.invoice_line_ids, [{
            'quantity': 1.0,
            'price_unit': 800.0,
            'price_subtotal': 800.0,
            'balance': 800.0,
            'tax_ids': self.tax_purchase_b.ids,
        }])

        # In case a unit price is already set we do not update the unit price
        invoice_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        invoice_form.partner_id = self.test_partners[0]
        invoice_form.invoice_date = self.frozen_today
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.price_unit = 42.0
            invoice_line_form.name = 'product_a'
        invoice = invoice_form.save()

        self.assertRecordValues(invoice.invoice_line_ids, [{
            'quantity': 1.0,
            'price_unit': 42.0,
            'price_subtotal': 42.0,
            'balance': 42.0,
            'tax_ids': self.tax_purchase_b.ids,
        }])

        # In case a tax is already set we do not update the taxes
        invoice_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        invoice_form.partner_id = self.test_partners[0]
        invoice_form.invoice_date = self.frozen_today
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.tax_ids = self.tax_purchase_a
            invoice_line_form.name = 'product_a'
        invoice = invoice_form.save()

        self.assertRecordValues(invoice.invoice_line_ids, [{
            'quantity': 1.0,
            'price_unit': 800.0,
            'price_subtotal': 800.0,
            'balance': 800.0,
            'tax_ids': self.tax_purchase_a.ids,
        }])
