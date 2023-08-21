# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.stock_account.tests.test_stockvaluation import _create_accounting_data
from odoo.tests.common import tagged, Form
from odoo import fields


@tagged("post_install", "-at_install")
class TestAccountMove(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        (
            cls.stock_input_account,
            cls.stock_output_account,
            cls.stock_valuation_account,
            cls.expense_account,
            cls.stock_journal,
        ) = _create_accounting_data(cls.env)

        # `all_categ` should not be altered, so we can test the `post_init` hook of `stock_account`
        cls.all_categ = cls.env.ref('product.product_category_all')

        cls.auto_categ = cls.env['product.category'].create({
            'name': 'child_category',
            'parent_id': cls.all_categ.id,
            "property_stock_account_input_categ_id": cls.stock_input_account.id,
            "property_stock_account_output_categ_id": cls.stock_output_account.id,
            "property_stock_valuation_account_id": cls.stock_valuation_account.id,
            "property_stock_journal": cls.stock_journal.id,
            "property_valuation": "real_time",
            "property_cost_method": "standard",
        })
        cls.product_A = cls.env["product.product"].create(
            {
                "name": "Product A",
                "type": "product",
                "default_code": "prda",
                "categ_id": cls.auto_categ.id,
                "taxes_id": [(5, 0, 0)],
                "supplier_taxes_id": [(5, 0, 0)],
                "lst_price": 100.0,
                "standard_price": 10.0,
                "property_account_income_id": cls.company_data["default_account_revenue"].id,
                "property_account_expense_id": cls.company_data["default_account_expense"].id,
            }
        )

    def test_standard_perpetual_01_mc_01(self):
        rate = self.currency_data["rates"].sorted()[0].rate

        move_form = Form(self.env["account.move"].with_context(default_move_type="out_invoice"))
        move_form.partner_id = self.partner_a
        move_form.currency_id = self.currency_data["currency"]
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_A
            line_form.tax_ids.clear()
        invoice = move_form.save()

        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_total)
        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_residual)
        self.assertEqual(len(invoice.mapped("line_ids")), 2)
        self.assertEqual(len(invoice.mapped("line_ids.currency_id")), 1)

        invoice._post()

        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_total)
        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_residual)
        self.assertEqual(len(invoice.mapped("line_ids")), 4)
        self.assertEqual(len(invoice.mapped("line_ids").filtered("is_anglo_saxon_line")), 2)
        self.assertEqual(len(invoice.mapped("line_ids.currency_id")), 2)

    def test_fifo_perpetual_01_mc_01(self):
        self.product_A.categ_id.property_cost_method = "fifo"
        rate = self.currency_data["rates"].sorted()[0].rate

        move_form = Form(self.env["account.move"].with_context(default_move_type="out_invoice"))
        move_form.partner_id = self.partner_a
        move_form.currency_id = self.currency_data["currency"]
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_A
            line_form.tax_ids.clear()
        invoice = move_form.save()

        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_total)
        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_residual)
        self.assertEqual(len(invoice.mapped("line_ids")), 2)
        self.assertEqual(len(invoice.mapped("line_ids.currency_id")), 1)

        invoice._post()

        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_total)
        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_residual)
        self.assertEqual(len(invoice.mapped("line_ids")), 4)
        self.assertEqual(len(invoice.mapped("line_ids").filtered("is_anglo_saxon_line")), 2)
        self.assertEqual(len(invoice.mapped("line_ids.currency_id")), 2)

    def test_average_perpetual_01_mc_01(self):
        self.product_A.categ_id.property_cost_method = "average"
        rate = self.currency_data["rates"].sorted()[0].rate

        move_form = Form(self.env["account.move"].with_context(default_move_type="out_invoice"))
        move_form.partner_id = self.partner_a
        move_form.currency_id = self.currency_data["currency"]
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_A
            line_form.tax_ids.clear()
        invoice = move_form.save()

        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_total)
        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_residual)
        self.assertEqual(len(invoice.mapped("line_ids")), 2)
        self.assertEqual(len(invoice.mapped("line_ids.currency_id")), 1)

        invoice._post()

        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_total)
        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_residual)
        self.assertEqual(len(invoice.mapped("line_ids")), 4)
        self.assertEqual(len(invoice.mapped("line_ids").filtered("is_anglo_saxon_line")), 2)
        self.assertEqual(len(invoice.mapped("line_ids.currency_id")), 2)

    def test_basic_bill(self):
        """
        When billing a storable product with a basic category (manual
        valuation), the account used should be the expenses one. This test
        checks the flow with two companies:
        - One that existed before the installation of `stock_account` (to test
        the post-install hook)
        - One created after the module installation
        """
        first_company = self.env['res.company'].browse(1)
        self.env.user.company_ids |= first_company
        basic_product = self.env['product.product'].create({
            'name': 'SuperProduct',
            'type': 'product',
            'categ_id': self.all_categ.id,
        })

        for company in (self.env.company | first_company):
            bill_form = Form(self.env['account.move'].with_company(company.id).with_context(default_move_type='in_invoice'))
            bill_form.partner_id = self.partner_a
            bill_form.invoice_date = fields.Date.today()
            with bill_form.invoice_line_ids.new() as line:
                line.product_id = basic_product
                line.price_unit = 100
            bill = bill_form.save()
            bill.action_post()

            product_accounts = basic_product.product_tmpl_id.with_company(company.id).get_product_accounts()
            self.assertEqual(bill.invoice_line_ids.account_id, product_accounts['expense'])
