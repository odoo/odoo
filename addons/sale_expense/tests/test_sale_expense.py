# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleExpense(TestExpenseCommon, TestSaleCommon):
    def _create_confirmed_sale_order(self):
        sale_order = self.env['sale.order'].create({
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
        sale_order.action_confirm()
        return sale_order

    def _approve_expense(self, expense):
        expense.action_submit()
        expense._do_approve()
        return expense

    def _get_post_wizard(self, expense):
        action = expense.action_post()
        return self.env['hr.expense.post.wizard'].with_context(action['context']).browse(action['res_id'])

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
            'reinvoice_policy': 'sales_price',
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
            'reinvoice_policy': 'cost',
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

    def test_attach_receipts_to_invoice_wizard_defaults(self):
        sale_order = self._create_confirmed_sale_order()

        cost_expense = self._approve_expense(self.create_expenses({
            'product_id': self.company_data['product_delivery_cost'].id,
            'quantity': 1,
            'sale_order_id': sale_order.id,
        }))
        cost_wizard = self._get_post_wizard(cost_expense)
        self.assertTrue(cost_wizard.show_attach_receipts_to_invoice)
        self.assertTrue(cost_wizard.attach_receipts_to_invoice)

        sales_price_product = self.env['product.product'].create({
            'name': 'Sales Price Expense',
            'reinvoice_policy': 'sales_price',
            'type': 'service',
            'can_be_expensed': True,
            'invoice_policy': 'delivery',
            'list_price': 50.0,
            'standard_price': 10.0,
        })
        sales_price_expense = self._approve_expense(self.create_expenses({
            'product_id': sales_price_product.id,
            'quantity': 1,
            'total_amount_currency': 100.0,
            'sale_order_id': sale_order.id,
        }))
        sales_price_wizard = self._get_post_wizard(sales_price_expense)
        self.assertTrue(sales_price_wizard.show_attach_receipts_to_invoice)
        self.assertFalse(sales_price_wizard.attach_receipts_to_invoice)

        not_reinvoiced_expense = self._approve_expense(self.create_expenses({
            'product_id': self.product_c.id,
            'quantity': 1,
            'total_amount_currency': 100.0,
        }))
        not_reinvoiced_wizard = self._get_post_wizard(not_reinvoiced_expense)
        self.assertFalse(not_reinvoiced_wizard.show_attach_receipts_to_invoice)
        self.assertFalse(not_reinvoiced_wizard.attach_receipts_to_invoice)

    def test_reinvoiced_expense_receipts_are_copied_to_customer_invoice(self):
        sale_order = self._create_confirmed_sale_order()
        expense = self._approve_expense(self.create_expenses({
            'product_id': self.company_data['product_delivery_cost'].id,
            'quantity': 1,
            'sale_order_id': sale_order.id,
        }))

        self.env['ir.attachment'].create([
            {
                'name': 'receipt_1.txt',
                'raw': b'receipt 1',
                'res_model': 'hr.expense',
                'res_id': expense.id,
            },
            {
                'name': 'receipt_2.txt',
                'raw': b'receipt 2',
                'res_model': 'hr.expense',
                'res_id': expense.id,
            },
        ])

        wizard = self._get_post_wizard(expense)
        self.assertTrue(wizard.attach_receipts_to_invoice)
        wizard.action_post_entry()

        invoice = sale_order._create_invoices()
        copied_receipts = invoice.attachment_ids.filtered(
            lambda attachment: attachment.name in {'receipt_1.txt', 'receipt_2.txt'}
        )

        self.assertEqual(len(copied_receipts), 2)
        self.assertTrue(any(
            '2 expense receipts attached from reinvoiced expenses.' in message.body
            for message in invoice.message_ids
        ))
        self.assertTrue(any(
            copied_receipts <= message.attachment_ids
            for message in invoice.message_ids
        ))

    def test_sales_price_receipts_are_copied_only_when_manually_enabled(self):
        sales_price_product = self.env['product.product'].create({
            'name': 'Sales Price Expense',
            'reinvoice_policy': 'sales_price',
            'type': 'service',
            'can_be_expensed': True,
            'invoice_policy': 'delivery',
            'list_price': 50.0,
            'standard_price': 10.0,
        })

        sale_order = self._create_confirmed_sale_order()
        expense = self._approve_expense(self.create_expenses({
            'product_id': sales_price_product.id,
            'quantity': 1,
            'sale_order_id': sale_order.id,
        }))
        self.env['ir.attachment'].create({
            'name': 'sales_price_receipt.txt',
            'raw': b'sales price receipt',
            'res_model': 'hr.expense',
            'res_id': expense.id,
        })

        wizard = self._get_post_wizard(expense)
        self.assertFalse(wizard.attach_receipts_to_invoice)
        wizard.action_post_entry()

        invoice = sale_order._create_invoices()
        self.assertFalse(invoice.attachment_ids.filtered(lambda attachment: attachment.name == 'sales_price_receipt.txt'))

        sale_order = self._create_confirmed_sale_order()
        expense = self._approve_expense(self.create_expenses({
            'product_id': sales_price_product.id,
            'quantity': 1,
            'sale_order_id': sale_order.id,
        }))
        self.env['ir.attachment'].create({
            'name': 'manual_sales_price_receipt.txt',
            'raw': b'manual sales price receipt',
            'res_model': 'hr.expense',
            'res_id': expense.id,
        })

        wizard = self._get_post_wizard(expense)
        wizard.attach_receipts_to_invoice = True
        wizard.action_post_entry()

        invoice = sale_order._create_invoices()
        self.assertTrue(invoice.attachment_ids.filtered(lambda attachment: attachment.name == 'manual_sales_price_receipt.txt'))
