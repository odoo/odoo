# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.addons.sale.tests.test_sale_common import TestSale
from openerp import workflow


class TestSaleExpense(TestSale):
    def test_sale_expense(self):
        """ Test the behaviour of sales orders when managing expenses """
        # create a so with a product invoiced on delivery
        prod = self.env.ref('product.product_product_1')
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
        prod_exp = self.env.ref('hr_expense.air_ticket')
        company = self.env.ref('base.main_company')
        journal = self.env['account.journal'].create({'name': 'Purchase Journal - Test', 'code': 'HRTPJ', 'type': 'purchase', 'company_id': company.id})
        account_payable = self.env['account.account'].create({'code': 'X1111', 'name': 'HR Expense - Test Payable Account', 'user_type_id': self.env.ref('account.data_account_type_payable').id, 'reconcile': True})
        exp = self.env['hr.expense.expense'].create({
            'name': 'Test Expense',
            'user_id': self.user.id,
            'line_ids': [(0, 0, {'product_id': prod_exp.id,
                                 'name': 'Air Travel',
                                 'analytic_account': so.project_id.id,
                                 'unit_amount': 700.0,
                                 })],
            'journal_id': journal.id,
            'employee_payable_account_id': account_payable.id,
        })
        cr, uid = self.cr, self.uid
        # Submit to Manager
        workflow.trg_validate(uid, 'hr.expense.expense', exp.id, 'confirm', cr)
        # Approve
        workflow.trg_validate(uid, 'hr.expense.expense', exp.id, 'validate', cr)
        # Create Expense Entries
        workflow.trg_validate(uid, 'hr.expense.expense', exp.id, 'done', cr)

        # expense should now be in sales order
        self.assertTrue(prod_exp in map(lambda so: so.product_id, so.order_line), 'Sale Expense: expense product should be in so')
        sol = so.order_line.filtered(lambda sol: sol.product_id.id == prod_exp.id)
        self.assertEqual((sol.price_unit, sol.qty_delivered), (700.0, 1.0), 'Sale Expense: error when invoicing an expense at cost')
        self.assertEqual(so.amount_total, init_price, 'Sale Expense: price of so not updated after adding expense')

        # create some expense and validate it (expense at sales price)
        init_price = so.amount_total
        prod_exp = self.env.ref('hr_expense.car_travel')
        exp = self.env['hr.expense.expense'].create({
            'name': 'Test Expense',
            'user_id': self.user.id,
            'line_ids': [(0, 0, {'product_id': prod_exp.id,
                                 'name': 'Car Travel',
                                 'analytic_account': so.project_id.id,
                                 'uom_id': self.env.ref('product.product_uom_km').id,
                                 'unit_amount': 0.15,
                                 'unit_quantity': 100,
                                 })],
            'journal_id': journal.id,
            'employee_payable_account_id': account_payable.id,
        })
        # Submit to Manager
        workflow.trg_validate(uid, 'hr.expense.expense', exp.id, 'confirm', cr)
        # Approve
        workflow.trg_validate(uid, 'hr.expense.expense', exp.id, 'validate', cr)
        # Create Expense Entries
        workflow.trg_validate(uid, 'hr.expense.expense', exp.id, 'done', cr)

        # expense should now be in sales order
        self.assertTrue(prod_exp in map(lambda so: so.product_id, so.order_line), 'Sale Expense: expense product should be in so')
        sol = so.order_line.filtered(lambda sol: sol.product_id.id == prod_exp.id)
        self.assertEqual((sol.price_unit, sol.qty_delivered), (0.32, 100.0), 'Sale Expense: error when invoicing an expense at cost')
        self.assertEqual(so.amount_total, init_price, 'Sale Expense: price of so not updated after adding expense')
        # self.assertTrue(so.invoice_status, 'no', 'Sale Expense: expenses should not impact the invoice_status of the so')

        # both expenses should be invoiced
        inv_id = so.action_invoice_create()
        inv = self.env['account.invoice'].browse(inv_id)
        self.assertEqual(inv.amount_total, 732.0, 'Sale Expense: invoicing of exepense is wrong')
