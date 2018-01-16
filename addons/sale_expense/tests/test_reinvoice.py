# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.addons.sale.tests.test_sale_common import TestCommonSaleNoChart


class TestReInvoice(TestExpenseCommon, TestCommonSaleNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestReInvoice, cls).setUpClass()

        cls.setUpExpenseProducts()

        # partner and SO
        cls.partner_customer = cls.env['res.partner'].create({
            'name': 'Ze Client',
            'email': 'client@agrolait.com',
            'property_account_payable_id': cls.account_payable.id,
        })

        cls.sale_order = cls.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': cls.partner_customer_usd.id,
            'partner_invoice_id': cls.partner_customer_usd.id,
            'partner_shipping_id': cls.partner_customer_usd.id,
        })

    def test_at_cost(self):
        """ Test invoicing expenses at cost for product based on delivered and ordered quantities. """
        # create SO line and confirm SO (with only one line)
        sale_order_line = self.env['sale.order.line'].create({
            'name': self.product_ordered_cost.name,
            'product_id': self.product_ordered_cost.id,
            'product_uom_qty': 2,
            'product_uom': self.product_ordered_cost.uom_id.id,
            'price_unit': self.product_ordered_cost.list_price,
            'order_id': self.sale_order.id,
        })
        sale_order_line.product_id_change()
        self.sale_order.onchange_partner_id()
        self.sale_order._compute_tax_id()
        self.sale_order.action_confirm()

        self.assertTrue(self.sale_order.analytic_account_id, "Confirming SO with an expense product should trigger the analytic account creation")

        # create expense lines
        expense1 = self.env['hr.expense'].create({
            'name': 'Expense for ordered product',
            'employee_id': self.employee.id,
            'product_id': self.product_ordered_cost.id,
            'unit_amount': 12,
            'quantity': 2,
            'sheet_id': self.expense_sheet.id,
            'sale_order_id': self.sale_order.id,
            'analytic_account_id': self.sale_order.analytic_account_id.id,
        })
        expense1._onchange_product_id()
        expense2 = self.env['hr.expense'].create({
            'name': 'Expense for delivered product',
            'employee_id': self.employee.id,
            'product_id': self.product_deliver_cost.id,
            'unit_amount': 15,
            'quantity': 1,
            'sheet_id': self.expense_sheet.id,
            'sale_order_id': self.sale_order.id,
            'analytic_account_id': self.sale_order.analytic_account_id.id,
        })
        expense2._onchange_product_id()

        # approve and generate entries
        self.expense_sheet.approve_expense_sheets()
        self.expense_sheet.action_sheet_move_create()

        self.assertEquals(len(self.sale_order.order_line), 3, "There should be 3 lines on the SO")
        self.assertEquals(sale_order_line.qty_delivered, 0, "Exising SO line should not be impacted by reinvoicing product at cost")

        sol_ordered = self.sale_order.order_line.filtered(lambda sol: sol.product_id == self.product_ordered_cost and sol != sale_order_line)
        self.assertTrue(sol_ordered, "A new line with ordered expense should have been created on expense report posting")
        self.assertEquals(sol_ordered.price_unit, expense1.unit_amount, "The unit price of new SO line should be the one from the expense (at cost)")
        self.assertEquals(sol_ordered.product_uom_qty, 0, "The ordered quantity of new SO line should be zero")
        self.assertEquals(sol_ordered.qty_delivered, expense1.quantity, "The delivered quantity of new SO line should be the one from the expense")

        sol_deliver = self.sale_order.order_line.filtered(lambda sol: sol.product_id == self.product_deliver_cost and sol != sale_order_line)
        self.assertTrue(sol_deliver, "A new line with delivered expense should have been created on expense report posting")
        self.assertEquals(sol_deliver.price_unit, expense2.unit_amount, "The unit price of new SO line should be the one from the expense (at cost)")
        self.assertEquals(sol_deliver.product_uom_qty, 0, "The ordered quantity of new SO line should be zero")
        self.assertEquals(sol_deliver.qty_delivered, expense2.quantity, "The delivered quantity of new SO line should be the one from the expense")

    def test_sales_price_ordered(self):
        """ Test invoicing expenses at sales price for product based on ordered quantities. """
        # confirm SO (with no line)
        self.sale_order._compute_tax_id()
        self.sale_order.action_confirm()
        self.assertFalse(self.sale_order.analytic_account_id, "Confirming SO with no expense product should not trigger the analytic account creation")

        # create expense lines
        expense1 = self.env['hr.expense'].create({
            'name': 'Expense for ordered product at sales price',
            'employee_id': self.employee.id,
            'product_id': self.product_order_sales_price.id,
            'unit_amount': 15,
            'quantity': 2,
            'sheet_id': self.expense_sheet.id,
            'sale_order_id': self.sale_order.id,
            'analytic_account_id': self.sale_order.analytic_account_id.id,
        })
        expense1._onchange_product_id()

        # approve and generate entries
        self.expense_sheet.approve_expense_sheets()
        self.expense_sheet.action_sheet_move_create()

        self.assertTrue(self.sale_order.analytic_account_id, "Posting expense with an expense product should trigger the analytic account creation on SO")
        self.assertEquals(self.sale_order.analytic_account_id, expense1.analytic_account_id, "SO analytic account should be the same for the expense")
        self.assertEquals(len(self.sale_order.order_line), 1, "A new So line should have been created on expense report posting")

        sol_ordered = self.sale_order.order_line.filtered(lambda sol: sol.product_id == expense1.product_id)
        self.assertTrue(sol_ordered, "A new line with ordered expense should have been created on expense report posting")
        self.assertEquals(sol_ordered.price_unit, 10, "The unit price of new SO line should be the one from the expense (at sales price)")
        self.assertEquals(sol_ordered.product_uom_qty, 0, "The ordered quantity of new SO line should be zero")
        self.assertEquals(sol_ordered.qty_delivered, expense1.quantity, "The delivered quantity of new SO line should be the one from the expense")

    def test_sales_price_delivered(self):
        """ Test invoicing expenses at sales price for product based on delivered quantities. Check the existing SO line is incremented. """
        # create SO line and confirm SO (with only one line)
        sale_order_line = self.env['sale.order.line'].create({
            'name': self.product_deliver_sales_price.name,
            'product_id': self.product_deliver_sales_price.id,
            'product_uom_qty': 2,
            'product_uom': self.product_deliver_sales_price.uom_id.id,
            'price_unit': self.product_deliver_sales_price.list_price,
            'order_id': self.sale_order.id,
        })
        sale_order_line.product_id_change()
        self.sale_order._compute_tax_id()
        self.sale_order.action_confirm()

        self.assertTrue(self.sale_order.analytic_account_id, "Confirming SO with an expense product should trigger the analytic account creation")

        # create expense lines
        expense1 = self.env['hr.expense'].create({
            'name': 'Expense for delivered product at sales price',
            'employee_id': self.employee.id,
            'product_id': self.product_deliver_sales_price.id,
            'unit_amount': 15,
            'quantity': 3,
            'sheet_id': self.expense_sheet.id,
            'sale_order_id': self.sale_order.id,
            'analytic_account_id': self.sale_order.analytic_account_id.id,
        })
        expense1._onchange_product_id()

        # approve and generate entries
        self.expense_sheet.approve_expense_sheets()
        self.expense_sheet.action_sheet_move_create()

        self.assertEquals(len(self.sale_order.order_line), 1, "No SO line should have been created (or removed) on expense report posting")

        self.assertEquals(sale_order_line.price_unit, 10, "The unit price of SO line should be the same")
        self.assertEquals(sale_order_line.product_uom_qty, 2, "The ordered quantity of new SO line should be zero")
        self.assertEquals(sale_order_line.qty_delivered, expense1.quantity, "The delivered quantity of SO line should have been incremented")

    def test_no_expense(self):
        """ Test invoicing expenses with no policy. Check nothing happen. """
        # confirm SO
        sale_order_line = self.env['sale.order.line'].create({
            'name': self.product_no_expense.name,
            'product_id': self.product_no_expense.id,
            'product_uom_qty': 2,
            'product_uom': self.product_no_expense.uom_id.id,
            'price_unit': self.product_no_expense.list_price,
            'order_id': self.sale_order.id,
        })
        self.sale_order._compute_tax_id()
        self.sale_order.action_confirm()

        self.assertFalse(self.sale_order.analytic_account_id, "Confirming SO with an no-expense product should not trigger the analytic account creation")

        # create expense lines
        expense1 = self.env['hr.expense'].create({
            'name': 'Expense for no expense product',
            'employee_id': self.employee.id,
            'product_id': self.product_no_expense.id,
            'unit_amount': 15,
            'quantity': 3,
            'sheet_id': self.expense_sheet.id,
            'sale_order_id': self.sale_order.id,
            'analytic_account_id': self.sale_order.analytic_account_id.id,
        })
        expense1._onchange_product_id()

        # approve and generate entries
        self.expense_sheet.approve_expense_sheets()
        self.expense_sheet.action_sheet_move_create()

        self.assertTrue(self.sale_order.analytic_account_id, "Posting expense with an expense product (even with no expense pilocy) should trigger the analytic account creation")
        self.assertEquals(self.sale_order.analytic_account_id, expense1.analytic_account_id, "SO analytic account should be the same for the expense")
        self.assertEquals(len(self.sale_order.order_line), 1, "No SO line should have been created (or removed) on expense report posting")

        self.assertEquals(sale_order_line.price_unit, self.product_no_expense.list_price, "The unit price of SO line should be the same")
        self.assertEquals(sale_order_line.product_uom_qty, 2, "The ordered quantity of SO line should be two")
        self.assertEquals(sale_order_line.qty_delivered, 0, "The delivered quantity of SO line should have been incremented")
