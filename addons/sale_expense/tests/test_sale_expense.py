# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.exceptions import UserError
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
        self.post_expenses(expense)

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
        self.post_expenses(expense_2)

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
        self.post_expenses(expense)

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

        def create_attachments(vals):
            return self.env['ir.attachment'].sudo().create([{
                'name': f"{val['name']}.txt",
                'raw': bytes(val['name'], 'utf-8'),
                'res_model': 'hr.expense',
                'res_id': val['expense_id'],
            } for val in vals])

        def get_attachments_linked_to_sale_order(sale_order_id):
            return self.env['ir.attachment'].search([
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', sale_order_id),
            ])

        def select(attachments, selected):
            return [{
                'id': attachment.id, 'name': attachment.name, 'selected': is_selected
            } for (attachment, is_selected) in zip(attachments, selected)]

        # At cost: receipts are attached to the customer invoice by default.
        sale_order = create_confirmed_sale_order()
        expense = approve_expense(self.create_expenses({
            'product_id': self.company_data['product_delivery_cost'].id,
            'quantity': 1,
            'sale_order_id': sale_order.id,
        }))
        attachments = create_attachments([
            {'name': 'receipt_1', 'expense_id': expense.id},
            {'name': 'receipt_2', 'expense_id': expense.id},
        ])

        # The button to fetch attachments on sale order from expenses is visible
        self.assertTrue(sale_order.is_linked_to_expense_with_attachment)
        action = sale_order.action_copy_reinvoiced_expense_receipts()
        wizard = self.env['expense.attachment.selection.wizard'].browse(action['res_id'])
        # sort to ease tests
        wizard.selected_attachments = sorted(wizard.selected_attachments, key=lambda att: att['name'])
        self.assertListEqual(wizard.selected_attachments, select(attachments, [True, True]))

        # import only 1 attachment
        wizard.selected_attachments = select(attachments, [True, False])
        wizard.action_import_attachments()
        attachment_linked_to_sale_order = get_attachments_linked_to_sale_order(sale_order.id)
        self.assertRecordValues(attachment_linked_to_sale_order, [{'name': attachments[0].name, 'checksum': attachments[0].checksum}])
        self.assertNotEqual(attachments[0].id, attachment_linked_to_sale_order.id)

        # create a new wizard, should show only the attachment not imported yet
        self.assertTrue(sale_order.is_linked_to_expense_with_attachment)
        action = sale_order.action_copy_reinvoiced_expense_receipts()
        wizard = self.env['expense.attachment.selection.wizard'].browse(action['res_id'])
        self.assertListEqual(wizard.selected_attachments, select(attachments[1], [True]))
        wizard.action_import_attachments()
        attachments_linked_to_sale_order = get_attachments_linked_to_sale_order(sale_order.id)

        self.assertRecordValues(attachments_linked_to_sale_order.sorted('name'), [
            {'name': attachments[0].name, 'checksum': attachments[0].checksum},
            {'name': attachments[1].name, 'checksum': attachments[1].checksum},
        ])
        self.assertFalse(set(attachments.ids) & set(attachments_linked_to_sale_order.ids))
        # No more attachments to import (need to invalidate cache to make sure the field is computed again)
        self.env['sale.order']._invalidate_cache(fnames=['is_linked_to_expense_with_attachment'])
        self.assertFalse(sale_order.is_linked_to_expense_with_attachment)

        new_attachments = create_attachments([
            {'name': 'receipt_4', 'expense_id': expense.id},
            {'name': 'receipt_5', 'expense_id': expense.id},
        ])
        # create an attachment on another sale to inject it in the wizard -> should be refused
        so = create_confirmed_sale_order()
        injected_attachment = self.env['ir.attachment'].create([{
            'name': 'receipt_3.txt',
            'raw': b'receipt_3',
            'res_model': 'sale.order',
            'res_id': so.id,
        }])
        action = sale_order.action_copy_reinvoiced_expense_receipts()
        wizard = self.env['expense.attachment.selection.wizard'].browse(action['res_id'])
        wizard.selected_attachments = sorted(wizard.selected_attachments, key=lambda att: att['name'])
        self.assertListEqual(wizard.selected_attachments, select(new_attachments, [True, True]))
        wizard.selected_attachments = select(new_attachments, [False, False])
        with self.assertRaises(UserError):
            wizard.action_import_attachments()

        wizard.selected_attachments = select((new_attachments + injected_attachment), [True, True, True])

        wizard.action_import_attachments()
        linked_attachments = get_attachments_linked_to_sale_order(sale_order.id)
        self.assertRecordValues(linked_attachments.sorted('name'), [
            {'name': attachments[0].name, 'checksum': attachments[0].checksum},
            {'name': attachments[1].name, 'checksum': attachments[1].checksum},
            {'name': new_attachments[0].name, 'checksum': new_attachments[0].checksum},
            {'name': new_attachments[1].name, 'checksum': new_attachments[1].checksum},
        ])
        self.assertFalse((attachments + new_attachments) & linked_attachments)
