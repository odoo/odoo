# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, AccessError

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


class TestAccountEntry(TestExpenseCommon):
    """
    Check journal entries when the expense product is having tax which is tax included.
    """

    def setUp(self):
        super(TestAccountEntry, self).setUp()

        self.setUpAdditionalAccounts()

        self.product_expense = self.env['product.product'].create({
            'name': "Delivered at cost",
            'standard_price': 700,
            'list_price': 700,
            'type': 'consu',
            'supplier_taxes_id': [(6, 0, [self.tax.id])],
            'default_code': 'CONSU-DELI-COST',
            'taxes_id': False,
            'property_account_expense_id': self.account_expense.id,
        })

    def test_account_entry(self):
        """ Checking accounting move entries and analytic entries when submitting expense """
        expense = self.env['hr.expense.sheet'].create({
            'name': 'Expense for John Smith',
            'employee_id': self.employee.id,
        })
        expense_line = self.env['hr.expense'].create({
            'name': 'Car Travel Expenses',
            'employee_id': self.employee.id,
            'product_id': self.product_expense.id,
            'unit_amount': 700.00,
            'tax_ids': [(6, 0, [self.tax.id])],
            'sheet_id': expense.id,
            'analytic_account_id': self.analytic_account.id,
        })
        expense_line._onchange_product_id()
        # State should default to draft
        self.assertEquals(expense.state, 'draft', 'Expense should be created in Draft state')
        # Submitted to Manager
        expense.action_submit_sheet()
        self.assertEquals(expense.state, 'submit', 'Expense is not in Reported state')
        # Approve
        expense.approve_expense_sheets()
        self.assertEquals(expense.state, 'approve', 'Expense is not in Approved state')
        # Create Expense Entries
        expense.action_sheet_move_create()
        self.assertEquals(expense.state, 'post', 'Expense is not in Waiting Payment state')
        self.assertTrue(expense.account_move_id.id, 'Expense Journal Entry is not created')

        # [(line.debit, line.credit, line.tax_line_id.id) for line in self.expense.expense_line_ids.account_move_id.line_ids]
        # should git this result [(0.0, 700.0, False), (63.64, 0.0, 179), (636.36, 0.0, False)]
        for line in expense.account_move_id.line_ids:
            if line.credit:
                self.assertAlmostEquals(line.credit, 700.00)
                self.assertEquals(len(line.analytic_line_ids), 0, "The credit move line should not have analytic lines")
                self.assertFalse(line.product_id, "Product of credit move line should be false")
            else:
                if not line.tax_line_id == self.tax:
                    self.assertAlmostEquals(line.debit, 636.36)
                    self.assertEquals(len(line.analytic_line_ids), 1, "The debit move line should have 1 analytic lines")
                    self.assertEquals(line.product_id, self.product_expense, "Product of debit move line should be the one from the expense")
                else:
                    self.assertAlmostEquals(line.debit, 63.64)
                    self.assertEquals(len(line.analytic_line_ids), 0, "The tax move line should not have analytic lines")
                    self.assertFalse(line.product_id, "Product of tax move line should be false")

        self.assertEquals(self.analytic_account.line_ids, expense.account_move_id.mapped('line_ids.analytic_line_ids'))
        self.assertEquals(len(self.analytic_account.line_ids), 1, "Analytic Account should have only one line")
        self.assertAlmostEquals(self.analytic_account.line_ids[0].amount, -636.36, "Amount on the only AAL is wrong")
        self.assertEquals(self.analytic_account.line_ids[0].product_id, self.product_expense, "Product of AAL should be the one from the expense")

    def test_account_entry_multi_currency(self):
        """ Checking accounting move entries and analytic entries when submitting expense. With
            multi-currency. And taxes. """

        # Clean-up the rates
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", [self.env.ref('base.USD').id, self.env.user.company_id.id])
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'currency_id': self.env.ref('base.EUR').id,
            'company_id': self.env.user.company_id.id,
            'rate': 2.0,
            'name': '2010-01-01',
        })

        expense = self.env['hr.expense.sheet'].create({
            'name': 'Expense for Dick Tracy',
            'employee_id': self.employee.id,
        })
        expense_line = self.env['hr.expense'].create({
            'name': 'Choucroute Saucisse',
            'employee_id': self.employee.id,
            'product_id': self.product_expense.id,
            'unit_amount': 700.00,
            'tax_ids': [(6, 0, [self.tax.id])],
            'sheet_id': expense.id,
            'analytic_account_id': self.analytic_account.id,
            'currency_id': self.env.ref('base.EUR').id,
        })
        expense_line._onchange_product_id()
        # State should default to draft
        self.assertEquals(expense.state, 'draft', 'Expense should be created in Draft state')
        # Submitted to Manager
        expense.action_submit_sheet()
        self.assertEquals(expense.state, 'submit', 'Expense is not in Reported state')
        # Approve
        expense.approve_expense_sheets()
        self.assertEquals(expense.state, 'approve', 'Expense is not in Approved state')
        # Create Expense Entries
        expense.action_sheet_move_create()
        self.assertEquals(expense.state, 'post', 'Expense is not in Waiting Payment state')
        self.assertTrue(expense.account_move_id.id, 'Expense Journal Entry is not created')

        # Should get this result [(0.0, 350.0, -700.0), (318.18, 0.0, 636.36), (31.82, 0.0, 63.64)]
        for line in expense.account_move_id.line_ids:
            if line.credit:
                self.assertAlmostEquals(line.credit, 350.0)
                self.assertAlmostEquals(line.amount_currency, -700.0)
                self.assertEquals(len(line.analytic_line_ids), 0, "The credit move line should not have analytic lines")
                self.assertFalse(line.product_id, "Product of credit move line should be false")
            else:
                if not line.tax_line_id == self.tax:
                    self.assertAlmostEquals(line.debit, 318.18)
                    self.assertAlmostEquals(line.amount_currency, 636.36)
                    self.assertEquals(len(line.analytic_line_ids), 1, "The debit move line should have 1 analytic lines")
                    self.assertEquals(line.product_id, self.product_expense, "Product of debit move line should be the one from the expense")
                else:
                    self.assertAlmostEquals(line.debit, 31.82)
                    self.assertAlmostEquals(line.amount_currency, 63.64)
                    self.assertEquals(len(line.analytic_line_ids), 0, "The tax move line should not have analytic lines")
                    self.assertFalse(line.product_id, "Product of tax move line should be false")

        self.assertEquals(self.analytic_account.line_ids, expense.account_move_id.mapped('line_ids.analytic_line_ids'))
        self.assertEquals(len(self.analytic_account.line_ids), 1, "Analytic Account should have only one line")
        self.assertAlmostEquals(self.analytic_account.line_ids[0].amount, -318.18, "Amount on the only AAL is wrong")
        self.assertAlmostEquals(self.analytic_account.line_ids[0].currency_id, self.env.user.company_id.currency_id, "Currency on the only AAL is wrong")
        self.assertEquals(self.analytic_account.line_ids[0].product_id, self.product_expense, "Product of AAL should be the one from the expense")

    def test_expense_from_email(self):
        user_demo = self.env.ref('base.user_demo')
        self.tax.price_include = False

        message_parsed = {
            'message_id': 'the-world-is-a-ghetto',
            'subject': '[EXP_AF] 9876',
            'email_from': 'mark.brown23@example.com',
            'to': 'catchall@yourcompany.com',
            'body': "Don't you know, that for me, and for you",
            'attachments': [],
        }

        expense = self.env['hr.expense'].message_new(message_parsed)

        air_ticket = self.env.ref("hr_expense.air_ticket")
        self.assertEquals(expense.product_id, air_ticket)
        self.assertEquals(expense.tax_ids.ids, [])
        self.assertEquals(expense.total_amount, 9876.0)
        self.assertTrue(expense.employee_id in user_demo.employee_ids)

class TestExpenseRights(TestExpenseCommon):

    @classmethod
    def setUpClass(cls):
        super(TestExpenseRights, cls).setUpClass()

    def test_expense_create(self):
        # Employee should be able to create an Expense
        self.env['hr.expense'].sudo(self.user_employee.id).create({
            'name': 'Batmobile repair',
            'employee_id': self.employee.id,
            'product_id': self.product_1.id,
            'unit_amount': 1,
            'quantity': 1,
        })

        # Employee should not be able to create an Expense for someone else
        with self.assertRaises(AccessError):
            self.env['hr.expense'].sudo(self.user_employee.id).create({
                'name': 'Superboy costume washing',
                'employee_id': self.emp_emp2.id,
                'product_id': self.product_2.id,
                'unit_amount': 1,
                'quantity': 1,
            })

    def test_expense_approve(self):
        sheet = self.env['hr.expense.sheet'].create({
            'name': 'Furnitures',
            'employee_id': self.emp_officer.id,
        })

        sheet_2 = self.env['hr.expense.sheet'].create({
            'name': 'Services',
            'employee_id': self.employee.id,
        })

        sheet_3 = self.env['hr.expense.sheet'].create({
            'name': 'Services 2',
            'employee_id': self.emp_emp2.id,
        })

        # Employee should not be able to approve expense sheet
        with self.assertRaises(UserError):
            sheet.sudo(self.user_officer).approve_expense_sheets()
        # Officer should not be able to approve own expense sheet
        with self.assertRaises(UserError):
            sheet.sudo(self.user_officer).approve_expense_sheets()
        sheet.sudo(self.user_manager).approve_expense_sheets()

        # Officer should be able to approve expense from his department
        sheet_2.sudo(self.user_officer).approve_expense_sheets()

        # Officer should not be able to approve expense sheet from another department
        with self.assertRaises(AccessError):
            sheet_3.sudo(self.user_officer).approve_expense_sheets()
        sheet_3.sudo(self.user_manager).approve_expense_sheets()

    def test_expense_refuse(self):
        sheet = self.env['hr.expense.sheet'].create({
            'name': 'Furnitures',
            'employee_id': self.emp_officer.id,
        })

        sheet_2 = self.env['hr.expense.sheet'].create({
            'name': 'Services',
            'employee_id': self.employee.id,
        })

        sheet_3 = self.env['hr.expense.sheet'].create({
            'name': 'Services 2',
            'employee_id': self.emp_emp2.id,
        })

        sheet.sudo(self.user_manager).approve_expense_sheets()
        sheet_2.sudo(self.user_manager).approve_expense_sheets()
        sheet_3.sudo(self.user_manager).approve_expense_sheets()

        # Employee should not be able to refuse expense sheet
        with self.assertRaises(UserError):
            sheet.sudo(self.user_employee).refuse_sheet('')
        # Officer should not be able to refuse own expense sheet
        with self.assertRaises(UserError):
            sheet.sudo(self.user_officer).refuse_sheet('')
        sheet.sudo(self.user_manager).refuse_sheet('')

        # Officer should be able to refuse expense from his department
        sheet_2.sudo(self.user_officer).refuse_sheet('')

        # Officer should not be able to refuse expense sheet from another department
        with self.assertRaises(AccessError):
            sheet_3.sudo(self.user_officer).refuse_sheet('')
        sheet_3.sudo(self.user_manager).refuse_sheet('')
