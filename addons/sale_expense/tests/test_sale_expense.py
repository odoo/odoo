# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleExpense(TestExpenseCommon, TestSaleCommon):
    
    def test_sale_expense(self):
        """ Test the behaviour of sales orders when managing expenses """

        # create a so with a product invoiced on delivery
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'name': self.company_data['product_delivery_no'].name,
                'product_id': self.company_data['product_delivery_no'].id,
                'product_uom_qty': 2,
                'product_uom': self.company_data['product_delivery_no'].uom_id.id,
                'price_unit': self.company_data['product_delivery_no'].list_price,
            })],
            'pricelist_id': self.env.ref('product.list0').id,
        })
        so._compute_tax_id()
        so.action_confirm()
        so._create_analytic_account()  # normally created at so confirmation when you use the right products
        init_price = so.amount_total

        # create some expense and validate it (expense at cost)
        # Submit to Manager
        sheet = self.env['hr.expense.sheet'].create({
            'name': 'Expense for John Smith',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
        })
        exp = self.env['hr.expense'].create({
            'name': 'Air Travel',
            'product_id': self.company_data['product_delivery_cost'].id,
            'analytic_account_id': so.analytic_account_id.id,
            'unit_amount': 621.54,
            'employee_id': self.expense_employee.id,
            'sheet_id': sheet.id,
            'sale_order_id': so.id,
        })
        # Approve
        sheet.approve_expense_sheets()
        # Create Expense Entries
        sheet.action_sheet_move_create()
        # expense should now be in sales order
        self.assertIn(self.company_data['product_delivery_cost'], so.mapped('order_line.product_id'), 'Sale Expense: expense product should be in so')
        sol = so.order_line.filtered(lambda sol: sol.product_id.id == self.company_data['product_delivery_cost'].id)
        self.assertEqual((sol.price_unit, sol.qty_delivered), (621.54, 1.0), 'Sale Expense: error when invoicing an expense at cost')
        self.assertEqual(so.amount_total, init_price + sol.price_unit, 'Sale Expense: price of so should be updated after adding expense')

        # create some expense and validate it (expense at sale price)
        init_price = so.amount_total
        prod_exp_2 = self.env['product.product'].create({
            'name': 'Car Travel',
            'expense_policy': 'sales_price',
            'type': 'service',
            'can_be_expensed': True,
            'invoice_policy': 'delivery',
            'list_price': 0.50,
            'uom_id': self.env.ref('uom.product_uom_km').id,
            'uom_po_id': self.env.ref('uom.product_uom_km').id,
        })
        # Submit to Manager
        sheet = self.env['hr.expense.sheet'].create({
            'name': 'Expense for John Smith',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
        })
        exp = self.env['hr.expense'].create({
            'name': 'Car Travel',
            'product_id': prod_exp_2.id,
            'analytic_account_id': so.analytic_account_id.id,
            'product_uom_id': self.env.ref('uom.product_uom_km').id,
            'unit_amount': 0.15,
            'quantity': 100,
            'employee_id': self.expense_employee.id,
            'sheet_id': sheet.id,
            'sale_order_id': so.id,
        })
        # Approve
        sheet.approve_expense_sheets()
        # Create Expense Entries
        sheet.action_sheet_move_create()
        # expense should now be in sales order
        self.assertIn(prod_exp_2, so.mapped('order_line.product_id'), 'Sale Expense: expense product should be in so')
        sol = so.order_line.filtered(lambda sol: sol.product_id.id == prod_exp_2.id)
        self.assertEqual((sol.price_unit, sol.qty_delivered), (prod_exp_2.list_price, 100.0), 'Sale Expense: error when invoicing an expense at cost')
        self.assertEqual(so.amount_untaxed, init_price + (prod_exp_2.list_price * 100.0), 'Sale Expense: price of so should be updated after adding expense')
        # self.assertTrue(so.invoice_status, 'no', 'Sale Expense: expenses should not impact the invoice_status of the so')

        # both expenses should be invoiced
        inv = so._create_invoices()
        self.assertEqual(inv.amount_untaxed, 621.54 + (prod_exp_2.list_price * 100.0), 'Sale Expense: invoicing of expense is wrong')
