# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleExpense(TestExpenseCommon, TestSaleCommon):

    _test_user_groups = None  # FIXME list needed groups

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
        self.assertEqual(so.expense_count, 1, "SO should recognize that an expense was created and linked to it")

        expense.action_submit()
        expense.action_approve()
        self.post_expenses_with_wizard(expense)

        # expense should now be in sales order
        self.assertEqual(so.expense_count, 1, "Changing the state of the expense shouldn't change the expense count on the SO")
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
        self.assertEqual(so.expense_count, 2, "SO should recognize that another expense was created and linked to it")

        expense_2.action_submit()
        expense_2.action_approve()
        self.post_expenses_with_wizard(expense_2)

        # expense should now be in sales order
        self.assertEqual(so.expense_count, 2, "Changing the state of the expense shouldn't change the expense count on the SO")
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

    def test_reinvoiced_expense_receipts_attachment_to_invoice(self):
        def create_confirmed_sale_order():
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

        def approve_expense(expense):
            expense.action_submit()
            expense._do_approve()
            return expense

        def get_post_wizard(expense):
            action = expense.action_post()
            return self.env['hr.expense.post.wizard'].with_context(action['context']).browse(action['res_id'])

        sales_price_product = self.env['product.product'].create({
            'name': 'Sales Price Expense',
            'reinvoice_policy': 'sales_price',
            'type': 'service',
            'can_be_expensed': True,
            'invoice_policy': 'delivery',
            'list_price': 50.0,
            'standard_price': 10.0,
        })

        # At cost: receipts are attached to the customer invoice by default.
        sale_order = create_confirmed_sale_order()
        expense = approve_expense(self.create_expenses({
            'product_id': self.company_data['product_delivery_cost'].id,
            'quantity': 1,
            'sale_order_id': sale_order.id,
        }))
        self.env['ir.attachment'].sudo().create([
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

        wizard = get_post_wizard(expense)
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

        # At sales price: receipts are not attached unless the accountant enables it.
        sale_order = create_confirmed_sale_order()
        expense = approve_expense(self.create_expenses({
            'product_id': sales_price_product.id,
            'quantity': 1,
            'sale_order_id': sale_order.id,
        }))
        self.env['ir.attachment'].sudo().create({
            'name': 'sales_price_receipt.txt',
            'raw': b'sales price receipt',
            'res_model': 'hr.expense',
            'res_id': expense.id,
        })

        wizard = get_post_wizard(expense)
        self.assertFalse(wizard.attach_receipts_to_invoice)
        wizard.action_post_entry()

        invoice = sale_order._create_invoices()
        self.assertFalse(invoice.attachment_ids.filtered(
            lambda attachment: attachment.name == 'sales_price_receipt.txt'
        ))

        # At sales price with manual opt-in: receipts are attached.
        sale_order = create_confirmed_sale_order()
        expense = approve_expense(self.create_expenses({
            'product_id': sales_price_product.id,
            'quantity': 1,
            'sale_order_id': sale_order.id,
        }))
        self.env['ir.attachment'].sudo().create({
            'name': 'manual_sales_price_receipt.txt',
            'raw': b'manual sales price receipt',
            'res_model': 'hr.expense',
            'res_id': expense.id,
        })

        wizard = get_post_wizard(expense)
        self.assertFalse(wizard.attach_receipts_to_invoice)
        wizard.attach_receipts_to_invoice = True
        wizard.action_post_entry()

        invoice = sale_order._create_invoices()
        self.assertTrue(invoice.attachment_ids.filtered(
            lambda attachment: attachment.name == 'manual_sales_price_receipt.txt'
        ))

    def test_expense_reinvoice_purchase_price(self):
        # re-invoiceable products
        product_with_cost = self.product_a
        product_with_cost.write({'standard_price': 1000, 'reinvoice_policy': 'sales_price'})
        product_with_no_cost = self.product_c
        product_with_no_cost.write({'reinvoice_policy': 'sales_price'})

        # create SO line and confirm SO (with only one line)
        sale_order = self.env['sale.order'].with_context(
            mail_create_nolog=True,
        ).sudo().create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': product_with_cost.name,
                'product_id': product_with_cost.id,
                'product_uom_qty': 2.0,
            })],
        })

        sale_order.action_confirm()

        expense = self.create_expenses([
            {
                # expense with zero cost product, with 15% tax
                'name': 'expense_1',
                'date': '2020-10-07',
                'product_id': product_with_no_cost.id,
                'total_amount_currency': 100,
                'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
                'sale_order_id': sale_order.id,
            },
            {
                # expense with zero cost product, with no tax
                'name': 'expense_2',
                'date': '2020-10-07',
                'product_id': product_with_no_cost.id,
                'total_amount_currency': 100,
                'tax_ids': False,
                'sale_order_id': sale_order.id
            },
            {
                # expense with product with cost (1000), with 15% tax
                'name': 'expense_3',
                'date': '2020-10-07',
                'product_id': product_with_cost.id,
                'quantity': 3,
                'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
                'sale_order_id': sale_order.id
            },
            {
                # expense with product with cost (1000), with no tax
                'name': 'expense_4',
                'date': '2020-10-07',
                'product_id': product_with_cost.id,
                'quantity': 5,
                'tax_ids': False,
                'sale_order_id': sale_order.id
            },
        ]).sorted('name')

        expense.action_submit()
        expense._do_approve()  # Skip duplicate wizard
        self.post_expenses_with_wizard(expense)

        self.assertAlmostEqual(sale_order.order_line[0].purchase_price, 1000.0)
        self.assertFalse(sale_order.order_line[0].is_expense)

        # Expense Lines
        for line, expected_purchase_price in zip(sale_order.order_line[1:], [86.96, 100.0, 869.5666667, 1000.0]):
            self.assertAlmostEqual(line.purchase_price, expected_purchase_price)
            self.assertTrue(line.is_expense)
