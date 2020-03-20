# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.test_sale_common import TestSaleCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleExpense(TestSaleCommon):
    def test_sale_expense(self):
        """ Test the behaviour of sales orders when managing expenses """
        # force the pricelist to have the same currency as the company
        self.env.ref('product.list0').currency_id = self.env.ref('base.main_company').currency_id

        # create a so with a product invoiced on delivery
        prod = self.env['product.product'].create({
            'name': 'A product',
            'invoice_policy': 'delivery',
            'list_price': 30.75,
            'uom_id': self.env.ref('uom.product_uom_hour').id,
            'uom_po_id': self.env.ref('uom.product_uom_hour').id,
        })
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': prod.name, 'product_id': prod.id, 'product_uom_qty': 2, 'product_uom': prod.uom_id.id, 'price_unit': prod.list_price})],
            'pricelist_id': self.env.ref('product.list0').id,
        })
        so.action_confirm()
        so._create_analytic_account()  # normally created at so confirmation when you use the right products
        init_price = so.amount_total

        # create some expense and validate it (expense at cost)
        prod_exp_1 = self.env['product.product'].create({
            'name': 'Air Ticket',
            'list_price': 700,
            'can_be_expensed': True,
            'expense_policy': 'cost',
            'type': 'service',
            'invoice_policy': 'delivery',
        })
        company = self.env.ref('base.main_company')
        journal = self.env['account.journal'].create({'name': 'Purchase Journal - Test', 'code': 'HRTPJ', 'type': 'purchase', 'company_id': company.id})
        employee = self.env['hr.employee'].create({'name': 'Test employee', 'user_id': self.user.id, 'address_home_id': self.user.partner_id.id})
        self.user.partner_id.property_account_payable_id = self.a_pay.id
        # Submit to Manager
        sheet = self.env['hr.expense.sheet'].create({
            'name': 'Expense for John Smith',
            'employee_id': employee.id,
            'journal_id': journal.id,
        })
        exp = self.env['hr.expense'].create({
            'name': 'Air Travel',
            'product_id': prod_exp_1.id,
            'analytic_account_id': so.analytic_account_id.id,
            'unit_amount': 621.54,
            'employee_id': employee.id,
            'sheet_id': sheet.id,
            'sale_order_id': so.id,
        })
        # Approve
        sheet.approve_expense_sheets()
        # Create Expense Entries
        sheet.action_sheet_move_create()
        # expense should now be in sales order
        self.assertIn(prod_exp_1, so.mapped('order_line.product_id'), 'Sale Expense: expense product should be in so')
        sol = so.order_line.filtered(lambda sol: sol.product_id.id == prod_exp_1.id)
        self.assertEqual((sol.price_unit, sol.qty_delivered), (621.54, 1.0), 'Sale Expense: error when invoicing an expense at cost')
        self.assertEqual(so.amount_total, init_price, 'Sale Expense: price of so not updated after adding expense')

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
            'employee_id': employee.id,
            'journal_id': journal.id,
        })
        exp = self.env['hr.expense'].create({
            'name': 'Car Travel',
            'product_id': prod_exp_2.id,
            'analytic_account_id': so.analytic_account_id.id,
            'product_uom_id': self.env.ref('uom.product_uom_km').id,
            'unit_amount': 0.15,
            'quantity': 100,
            'employee_id': employee.id,
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
        self.assertEqual(so.amount_total, init_price, 'Sale Expense: price of so not updated after adding expense')
        # self.assertTrue(so.invoice_status, 'no', 'Sale Expense: expenses should not impact the invoice_status of the so')

        # both expenses should be invoiced
        inv = so._create_invoices()
        self.assertEqual(inv.amount_untaxed, 621.54 + (prod_exp_2.list_price * 100.0), 'Sale Expense: invoicing of expense is wrong')
