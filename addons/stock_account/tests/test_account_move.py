# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.stock_account.tests.test_stockvaluation import _create_accounting_data
from odoo.tests.common import tagged, Form


@tagged("post_install", "-at_install")
class TestAccountMoveStockCommon(AccountTestInvoicingCommon):
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

        cls.product_A = cls.env["product.product"].create(
            {
                "name": "Product A",
                "type": "product",
                "default_code": "prda",
                "categ_id": cls.env.ref("product.product_category_all").id,
                "taxes_id": [(5, 0, 0)],
                "supplier_taxes_id": [(5, 0, 0)],
                "lst_price": 100.0,
                "standard_price": 10.0,
                "property_account_income_id": cls.company_data["default_account_revenue"].id,
                "property_account_expense_id": cls.company_data["default_account_expense"].id,
            }
        )
        cls.product_A.categ_id.write(
            {
                "property_stock_account_input_categ_id": cls.stock_input_account.id,
                "property_stock_account_output_categ_id": cls.stock_output_account.id,
                "property_stock_valuation_account_id": cls.stock_valuation_account.id,
                "property_stock_journal": cls.stock_journal.id,
                "property_valuation": "real_time",
                "property_cost_method": "standard",
            }
        )


@tagged("post_install", "-at_install")
class TestAccountMove(TestAccountMoveStockCommon):
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
        self.assertEqual(len(invoice.mapped("line_ids")), 2)
        self.assertEqual(len(invoice.mapped("line_ids.currency_id")), 1)

        invoice._post()

        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_total)
        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_residual)
        self.assertEqual(len(invoice.mapped("line_ids")), 4)
        self.assertEqual(len(invoice.mapped("line_ids").filtered(lambda l: l.display_type == 'cogs')), 2)
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
        self.assertEqual(len(invoice.mapped("line_ids")), 2)
        self.assertEqual(len(invoice.mapped("line_ids.currency_id")), 1)

        invoice._post()

        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_total)
        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_residual)
        self.assertEqual(len(invoice.mapped("line_ids")), 4)
        self.assertEqual(len(invoice.mapped("line_ids").filtered(lambda l: l.display_type == 'cogs')), 2)
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
        self.assertEqual(len(invoice.mapped("line_ids")), 2)
        self.assertEqual(len(invoice.mapped("line_ids.currency_id")), 1)

        invoice._post()

        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_total)
        self.assertAlmostEqual(self.product_A.lst_price * rate, invoice.amount_residual)
        self.assertEqual(len(invoice.mapped("line_ids")), 4)
        self.assertEqual(len(invoice.mapped("line_ids").filtered(lambda l: l.display_type == 'cogs')), 2)
        self.assertEqual(len(invoice.mapped("line_ids.currency_id")), 2)
