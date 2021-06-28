# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, Form


class TestSaleMrpKitBom(TransactionCase):

    def _create_product(self, name, type, price):
        return self.env['product.product'].create({
            'name': name,
            'type': type,
            'standard_price': price,
        })

    def test_sale_mrp_kit_bom_cogs(self):
        """Check invoice COGS aml after selling and delivering a product
        with Kit BoM having another product with Kit BoM as component"""

        # ----------------------------------------------
        # BoM of Kit A:
        #   - BoM Type: Kit
        #   - Quantity: 3
        #   - Components:
        #     * 2 x Kit B
        #     * 1 x Component A (Cost: $3)
        #
        # BoM of Kit B:
        #   - BoM Type: Kit
        #   - Quantity: 10
        #   - Components:
        #     * 2 x Component B (Cost: $4)
        #     * 3 x Component BB (Cost: $5)
        # ----------------------------------------------

        self.env.user.company_id.anglo_saxon_accounting = True
        self.stock_input_account = self.env['account.account'].create({
            'name': 'Stock Input',
            'code': 'StockIn',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
        })
        self.stock_output_account = self.env['account.account'].create({
            'name': 'Stock Output',
            'code': 'StockOut',
            'reconcile': True,
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
        })
        self.stock_valuation_account = self.env['account.account'].create({
            'name': 'Stock Valuation',
            'code': 'StockVal',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
        })
        self.expense_account = self.env['account.account'].create({
            'name': 'Expense Account',
            'code': 'Exp',
            'user_type_id': self.env.ref('account.data_account_type_expenses').id,
        })
        self.income_account = self.env['account.account'].create({
            'name': 'Income Account',
            'code': 'Inc',
            'user_type_id': self.env.ref('account.data_account_type_expenses').id,
        })
        self.stock_journal = self.env['account.journal'].create({
            'name': 'Stock Journal',
            'code': 'STJTEST',
            'type': 'general',
        })
        self.recv_account = self.env['account.account'].create({
            'name': 'account receivable',
            'code': 'RECV',
            'user_type_id': self.env.ref('account.data_account_type_receivable').id,
            'reconcile': True,
        })
        self.pay_account = self.env['account.account'].create({
            'name': 'account payable',
            'code': 'PAY',
            'user_type_id': self.env.ref('account.data_account_type_payable').id,
            'reconcile': True,
        })
        self.customer = self.env['res.partner'].create({
            'name': 'customer',
            'property_account_receivable_id': self.recv_account.id,
            'property_account_payable_id': self.pay_account.id,
        })
        self.journal_sale = self.env['account.journal'].create({
            'name': 'Sale Journal - Test',
            'code': 'AJ-SALE',
            'type': 'sale',
            'company_id': self.env.user.company_id.id,
        })

        self.component_a = self._create_product('Component A', 'consu', 3.00)
        self.component_b = self._create_product('Component B', 'consu', 4.00)
        self.component_bb = self._create_product('Component BB', 'consu', 5.00)
        self.kit_a = self._create_product('Kit A', 'product', 0.00)
        self.kit_b = self._create_product('Kit B', 'consu', 0.00)

        self.kit_a.write({
            'categ_id': self.env.ref('product.product_category_all').id,
            'property_account_expense_id': self.expense_account.id,
            'property_account_income_id': self.income_account.id,
        })
        self.kit_a.categ_id.write({
            'property_stock_account_input_categ_id': self.stock_input_account.id,
            'property_stock_account_output_categ_id': self.stock_output_account.id,
            'property_stock_valuation_account_id': self.stock_valuation_account.id,
            'property_stock_journal': self.stock_journal.id,
            'property_valuation': 'real_time',
        })

        # Create BoM for Kit A
        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = self.kit_a
        bom_product_form.product_tmpl_id = self.kit_a.product_tmpl_id
        bom_product_form.product_qty = 3.0
        bom_product_form.type = 'phantom'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.kit_b
            bom_line.product_qty = 2.0
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.component_a
            bom_line.product_qty = 1.0
        self.bom_a = bom_product_form.save()

        # Create BoM for Kit B
        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = self.kit_b
        bom_product_form.product_tmpl_id = self.kit_b.product_tmpl_id
        bom_product_form.product_qty = 10.0
        bom_product_form.type = 'phantom'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.component_b
            bom_line.product_qty = 2.0
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.component_bb
            bom_line.product_qty = 3.0
        self.bom_b = bom_product_form.save()

        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {
                    'name': self.kit_a.name,
                    'product_id': self.kit_a.id,
                    'product_uom_qty': 1.0,
                    'product_uom': self.kit_a.uom_id.id,
                    'price_unit': 1,
                    'tax_id': False,
                })],
        })
        so.action_confirm()
        so.picking_ids.move_lines.quantity_done = 1
        so.picking_ids.button_validate()

        invoice = so.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertAlmostEqual(stock_out_aml.credit, 2.53)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertAlmostEqual(cogs_aml.debit, 2.53)
        self.assertEqual(cogs_aml.credit, 0)
