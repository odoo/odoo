# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest import skip

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.stock_account.tests.test_stockvaluation import _create_accounting_data
from odoo.tests import Form, tagged
from odoo import fields, Command


@skip('Temporary to fast merge new valuation')
class TestAccountMoveStockCommon(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.other_currency = cls.setup_other_currency('EUR')

        (
            cls.stock_input_account,
            cls.stock_output_account,
            cls.stock_valuation_account,
            cls.expense_account,
            cls.income_account,
            cls.stock_journal,
        ) = _create_accounting_data(cls.env)

        # `all_categ` should not be altered, so we can test the `post_init` hook of `stock_account`
        cls.all_categ = cls.env.ref('product.product_category_goods')

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
                "is_storable": True,
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

        cls.branch_a = cls.setup_other_company(name="Branch A", parent_id=cls.env.company.id)


@tagged("post_install", "-at_install")
@skip('Temporary to fast merge new valuation')
class TestAccountMove(TestAccountMoveStockCommon):
    def test_standard_perpetual_01_mc_01(self):
        rate = self.other_currency.rate_ids.sorted()[0].rate

        move_form = Form(self.env["account.move"].with_context(default_move_type="out_invoice"))
        move_form.partner_id = self.partner_a
        move_form.currency_id = self.other_currency
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
        rate = self.other_currency.rate_ids.sorted()[0].rate

        move_form = Form(self.env["account.move"].with_context(default_move_type="out_invoice"))
        move_form.partner_id = self.partner_a
        move_form.currency_id = self.other_currency
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
        rate = self.other_currency.rate_ids.sorted()[0].rate

        move_form = Form(self.env["account.move"].with_context(default_move_type="out_invoice"))
        move_form.partner_id = self.partner_a
        move_form.currency_id = self.other_currency
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

    def test_storno_accounting(self):
        """Storno accounting uses negative numbers on debit/credit to cancel other moves.
        This test checks that we do the same for the anglosaxon lines when storno is enabled.
        """
        self.env.company.account_storno = True
        self.env.company.anglo_saxon_accounting = True

        move = self.env['account.move'].create({
            'move_type': 'out_refund',
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [
                (0, None, {'product_id': self.product_A.id}),
            ]
        })
        move.action_post()

        stock_output_line = move.line_ids.filtered(lambda l: l.account_id == self.stock_output_account)
        self.assertEqual(stock_output_line.debit, 0)
        self.assertEqual(stock_output_line.credit, -10)

        expense_line = move.line_ids.filtered(lambda l: l.account_id == self.product_A.property_account_expense_id)
        self.assertEqual(expense_line.debit, -10)
        self.assertEqual(expense_line.credit, 0)

    def test_standard_manual_tax_edit(self):
        ''' Test manually editing tax amount, cogs creation should not reset tax amount '''
        move_form = Form(self.env["account.move"].with_context(default_move_type="out_invoice"))
        move_form.partner_id = self.partner_a
        self.company_data["default_account_revenue"].write({
            'tax_ids': [(6, 0, [self.env.company.account_sale_tax_id.id])]
        })
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_A
        invoice = move_form.save()

        self.assertEqual(invoice.amount_total, 115)
        self.assertEqual(invoice.amount_untaxed, 100)
        self.assertEqual(invoice.amount_tax, 15)

        # simulate manual tax edit via widget
        tax_totals = invoice.tax_totals
        tax_totals['subtotals'][0]['tax_groups'][0]['tax_amount_currency'] = 14.0
        invoice.tax_totals = tax_totals

        self.assertEqual(len(invoice.mapped("line_ids")), 3)
        self.assertEqual(invoice.amount_total, 114)
        self.assertEqual(invoice.amount_untaxed, 100)
        self.assertEqual(invoice.amount_tax, 14)

        invoice._post()

        self.assertEqual(len(invoice.mapped("line_ids")), 5)
        self.assertEqual(invoice.amount_total, 114)
        self.assertEqual(invoice.amount_untaxed, 100)
        self.assertEqual(invoice.amount_tax, 14)

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
            'is_storable': True,
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

    def test_product_valuation_method_change_to_automated_negative_on_hand_qty(self):
        """ We have a product whose category has manual valuation and on-hand quantity is negative:
        Upon switching to an automated valuation method for the product category, the following
        entries should be generated in the stock journal:
            1. CREDIT to valuation account
            2. DEBIT to stock output account
        """
        stock_location = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id),
        ], limit=1).lot_stock_id
        categ = self.env['product.category'].create({'name': 'categ'})
        product = self.product_a
        product.write({
            'is_storable': True,
            'categ_id': categ.id,
        })

        out_picking = self.env['stock.picking'].create({
            'location_id': stock_location.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'picking_type_id': stock_location.warehouse_id.out_type_id.id,
        })
        sm = self.env['stock.move'].create({
            'product_id': product.id,
            'product_uom_qty': 1,
            'product_uom': product.uom_id.id,
            'location_id': out_picking.location_id.id,
            'location_dest_id': out_picking.location_dest_id.id,
            'picking_id': out_picking.id,
        })
        out_picking.action_confirm()
        sm.quantity = 1
        out_picking.button_validate()

        categ.write({
            'property_valuation': 'real_time',
            'property_stock_account_input_categ_id': self.stock_input_account.id,
            'property_stock_account_output_categ_id': self.stock_output_account.id,
            'property_stock_valuation_account_id': self.stock_valuation_account.id,
            'property_stock_journal': self.stock_journal.id,
        })

        amls = self.env['account.move.line'].search([('product_id', '=', product.id)]).sorted(
            # ensure the aml with the stock_valuation_account is the first one
            lambda amls: amls.account_id != self.stock_valuation_account
        )

        expected_valuation_line = {
            'account_id': self.stock_valuation_account.id,
            'credit': product.standard_price,
            'debit': 0,
        }
        expected_output_line = {
            'account_id': self.stock_output_account.id,
            'credit': 0,
            'debit': product.standard_price,
        }
        self.assertRecordValues(amls, [expected_valuation_line, expected_output_line])

    def test_stock_account_move_automated_not_standard_with_branch_company(self):
        """
        Test that the validation of a stock picking does not fail `_check_company`
        at the creation of the account move with sub company
        """
        branch_a = self.branch_a['company']
        self.env.user.company_id = branch_a

        self.auto_categ.write({'property_cost_method': 'average', 'property_valuation': 'real_time'})
        product = self.product_A
        product.write({'categ_id': self.auto_categ.id, 'standard_price': 300, 'company_id': branch_a.id})

        stock_location = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id),
        ], limit=1).lot_stock_id

        in_picking = self.env['stock.picking'].create({
            'location_id': stock_location.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'picking_type_id': stock_location.warehouse_id.in_type_id.id,
        })

        sm = self.env['stock.move'].create({
            'product_id': product.id,
            'product_uom_qty': 1,
            'product_uom': product.uom_id.id,
            'location_id': in_picking.location_id.id,
            'location_dest_id': in_picking.location_dest_id.id,
            'picking_id': in_picking.id,
        })
        in_picking.button_validate()
        self.assertEqual(sm.state, 'done')
        self.assertEqual(sm.account_move_ids.company_id, self.env.company)

    def test_cogs_analytic_accounting(self):
        """Check analytic distribution is correctly propagated to COGS lines"""
        self.env.company.anglo_saxon_accounting = True
        default_plan = self.env['account.analytic.plan'].create({
            'name': 'Default',
        })
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'Account 1',
            'plan_id': default_plan.id,
            'company_id': False,
        })

        move = self.env['account.move'].create({
            'move_type': 'out_refund',
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_A.id,
                    'analytic_distribution': {
                        analytic_account.id: 100,
                    },
                }),
            ]
        })
        move.action_post()

        cogs_line = move.line_ids.filtered(lambda l: l.account_id == self.product_A.property_account_expense_id)
        self.assertEqual(cogs_line.analytic_distribution, {str(analytic_account.id): 100})

    def test_cogs_account_branch_company(self):
        """Check branch company accounts are selected"""
        branch = self.branch_a['company']
        test_account = self.env['account.account'].with_company(branch.id).create({
            'name': '10001 Test Account',
            'code': 'STCKIN',
            'reconcile': True,
            'account_type': 'asset_current',
        })
        self.auto_categ.with_company(branch.id).property_valuation = "real_time"
        self.auto_categ.with_company(branch.id).property_stock_account_input_categ_id = test_account

        bill = self.env['account.move'].with_company(branch.id).with_context(default_move_type='in_invoice').create({
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_A.id,
                    'price_unit': 100,
                }),
            ],
        })

        self.assertEqual(bill.invoice_line_ids.account_id, test_account)

    def test_apply_inventory_adjustment_on_multiple_quants_simultaneously(self):
        products = self.product_a + self.product_b
        products.write({'is_storable': True, 'categ_id': self.auto_categ.id})
        stock_loc = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id),
        ], limit=1).lot_stock_id
        self.env['stock.quant']._update_available_quantity(self.product_a, stock_loc, 5)
        self.env['stock.quant']._update_available_quantity(self.product_b, stock_loc, 15)
        quants = products.stock_quant_ids
        quants.inventory_quantity = 10.0
        wizard = self.env['stock.inventory.adjustment.name'].create({'quant_ids': quants})
        wizard.action_apply()
        inv_adjustment_journal_items = self.env['account.move.line'].search([('product_id', 'in', products.ids)], order='id asc', limit=4)
        prod_a_accounts = self.product_a.product_tmpl_id.get_product_accounts()
        prod_b_accounts = self.product_b.product_tmpl_id.get_product_accounts()
        self.assertRecordValues(
            inv_adjustment_journal_items,
            [
                {'account_id': prod_a_accounts['income'].id, 'product_id': self.product_a.id},
                {'account_id': prod_a_accounts['stock_valuation'].id, 'product_id': self.product_a.id},
                {'account_id': prod_b_accounts['stock_valuation'].id, 'product_id': self.product_b.id},
                {'account_id': prod_b_accounts['expense'].id, 'product_id': self.product_b.id},
            ]
        )
