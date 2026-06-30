# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
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
            'order_line': [Command.create({
                'name': self.company_data['product_delivery_no'].name,
                'product_id': self.company_data['product_delivery_no'].id,
                'product_uom_qty': 2,
                'price_unit': self.company_data['product_delivery_no'].list_price,
            })],
        })
        so.action_confirm()
        analytic_account = self.env['account.analytic.account'].create(so._prepare_analytic_account_data())
        init_price = so.amount_total

        # create some expense and validate it (expense at cost)
        expense = self.create_expenses({
            'product_id': self.company_data['product_delivery_cost'].id,
            'analytic_distribution': {analytic_account.id: 100},
            'quantity': 11.30,
            'sale_order_id': so.id,
        })
        expense.action_submit()
        expense.action_approve()
        self.post_expenses_with_wizard(expense)

        # expense should now be in sales order
        self.assertIn(self.company_data['product_delivery_cost'], so.mapped('order_line.product_id'), 'Sale Expense: expense product should be in so')
        sol = so.order_line.filtered(lambda sol: sol.product_id.id == self.company_data['product_delivery_cost'].id)
        self.assertEqual((sol.price_unit, sol.qty_delivered), (55.0, 11.3), 'Sale Expense: error when invoicing an expense at cost')
        self.assertEqual(so.amount_total, init_price + expense.total_amount, 'Sale Expense: price of so should be updated after adding expense')
        self.assertEqual(sol.analytic_distribution, {str(analytic_account.id): 100})

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
            'standard_price': 0.15,
        })
        expense_2 = self.env['hr.expense'].create({
            'name': 'Car Travel',
            'product_id': prod_exp_2.id,
            'analytic_distribution': {analytic_account.id: 100},
            'quantity': 100,
            'employee_id': self.expense_employee.id,
            'sale_order_id': so.id,
        })
        expense_2.action_submit()
        expense_2.action_approve()
        self.post_expenses_with_wizard(expense_2)

        # expense should now be in sales order
        self.assertIn(prod_exp_2, so.mapped('order_line.product_id'), 'Sale Expense: expense product should be in so')
        sol = so.order_line.filtered(lambda sol: sol.product_id.id == prod_exp_2.id)
        self.assertEqual((sol.price_unit, sol.qty_delivered), (prod_exp_2.list_price, 100.0), 'Sale Expense: error when invoicing an expense at cost')
        self.assertEqual(so.amount_untaxed, init_price + (prod_exp_2.list_price * 100.0), 'Sale Expense: price of so should be updated after adding expense')

        # both expenses should be invoiced
        inv = so._create_invoices()
        self.assertEqual(inv.amount_untaxed, 621.5 + (prod_exp_2.list_price * 100.0), 'Sale Expense: invoicing of expense is wrong')

    def test_expense_multi_id_analytic_distribution(self):
        """
        Test conversion of analytic_distribution dict into account numbers when a hr.expense with an analytic_distribution
        having 2+ account ids
        """
        expensed_product = self.env['product.product'].create({
            'name': 'test product',
            'can_be_expensed': True,
            'type': 'service',
            'invoice_policy': 'order',
            'standard_price': 100,
            'expense_policy': 'cost',
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': self.product_b.id})],
        })
        sale_order.action_confirm()
        sale_order._create_invoices()

        analytic_account_3 = self.env['account.analytic.account'].create({
            'name': 'analytic_account_3',
            'plan_id': self.analytic_plan.id,
        })

        expense = self.create_expenses({
            'product_id': expensed_product.id,
            'quantity': 1000.00,
            'analytic_distribution': {
                f'{self.analytic_account_1.id},{self.analytic_account_2.id}': 60,
                f'{analytic_account_3.id}': 40,
            },
            'sale_order_id': sale_order.id,
        })
        expense.action_submit()
        expense.action_approve()
        self.post_expenses_with_wizard(expense)

        self.assertTrue(self.env['account.move'].search([('expense_ids', '=', expense.id)], limit=1))
