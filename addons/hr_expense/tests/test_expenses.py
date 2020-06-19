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
        # State should default to draft
        self.assertEqual(expense.state, 'draft', 'Expense should be created in Draft state')
        # Submitted to Manager
        expense.action_submit_sheet()
        self.assertEqual(expense.state, 'submit', 'Expense is not in Reported state')
        # Approve
        expense.approve_expense_sheets()
        self.assertEqual(expense.state, 'approve', 'Expense is not in Approved state')
        # Create Expense Entries
        expense.action_sheet_move_create()
        self.assertEqual(expense.state, 'post', 'Expense is not in Waiting Payment state')
        self.assertTrue(expense.account_move_id.id, 'Expense Journal Entry is not created')

        # [(line.debit, line.credit, line.tax_line_id.id) for line in self.expense.expense_line_ids.account_move_id.line_ids]
        # should git this result [(0.0, 700.0, False), (63.64, 0.0, 179), (636.36, 0.0, False)]
        for line in expense.account_move_id.line_ids:
            if line.credit:
                self.assertAlmostEqual(line.credit, 700.00)
                self.assertEqual(len(line.analytic_line_ids), 0, "The credit move line should not have analytic lines")
                self.assertFalse(line.product_id, "Product of credit move line should be false")
            else:
                if not line.tax_line_id == self.tax:
                    self.assertAlmostEqual(line.debit, 636.36)
                    self.assertEqual(len(line.analytic_line_ids), 1, "The debit move line should have 1 analytic lines")
                    self.assertEqual(line.product_id, self.product_expense, "Product of debit move line should be the one from the expense")
                else:
                    self.assertAlmostEqual(line.debit, 63.64)
                    self.assertEqual(len(line.analytic_line_ids), 0, "The tax move line should not have analytic lines")
                    self.assertFalse(line.product_id, "Product of tax move line should be false")

        self.assertEqual(self.analytic_account.line_ids, expense.account_move_id.mapped('line_ids.analytic_line_ids'))
        self.assertEqual(len(self.analytic_account.line_ids), 1, "Analytic Account should have only one line")
        self.assertAlmostEqual(self.analytic_account.line_ids[0].amount, -636.36, "Amount on the only AAL is wrong")
        self.assertEqual(self.analytic_account.line_ids[0].product_id, self.product_expense, "Product of AAL should be the one from the expense")

    def test_account_entry_multi_currency(self):
        """ Checking accounting move entries and analytic entries when submitting expense. With
            multi-currency. And taxes. """

        # Clean-up the rates
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", [self.env.ref('base.USD').id, self.env.company.id])
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'currency_id': self.env.ref('base.EUR').id,
            'company_id': self.env.company.id,
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
        # State should default to draft
        self.assertEqual(expense.state, 'draft', 'Expense should be created in Draft state')
        # Submitted to Manager
        expense.action_submit_sheet()
        self.assertEqual(expense.state, 'submit', 'Expense is not in Reported state')
        # Approve
        expense.approve_expense_sheets()
        self.assertEqual(expense.state, 'approve', 'Expense is not in Approved state')
        # Create Expense Entries
        expense.action_sheet_move_create()
        self.assertEqual(expense.state, 'post', 'Expense is not in Waiting Payment state')
        self.assertTrue(expense.account_move_id.id, 'Expense Journal Entry is not created')

        # Should get this result [(0.0, 350.0, -700.0), (318.18, 0.0, 636.36), (31.82, 0.0, 63.64)]
        for line in expense.account_move_id.line_ids:
            if line.credit:
                self.assertAlmostEqual(line.credit, 350.0)
                self.assertAlmostEqual(line.amount_currency, -700.0)
                self.assertEqual(len(line.analytic_line_ids), 0, "The credit move line should not have analytic lines")
                self.assertFalse(line.product_id, "Product of credit move line should be false")
            else:
                if not line.tax_line_id == self.tax:
                    self.assertAlmostEqual(line.debit, 318.18)
                    self.assertAlmostEqual(line.amount_currency, 636.36)
                    self.assertEqual(len(line.analytic_line_ids), 1, "The debit move line should have 1 analytic lines")
                    self.assertEqual(line.product_id, self.product_expense, "Product of debit move line should be the one from the expense")
                else:
                    self.assertAlmostEqual(line.debit, 31.82)
                    self.assertAlmostEqual(line.amount_currency, 63.64)
                    self.assertEqual(len(line.analytic_line_ids), 0, "The tax move line should not have analytic lines")
                    self.assertFalse(line.product_id, "Product of tax move line should be false")

        self.assertEqual(self.analytic_account.line_ids, expense.account_move_id.mapped('line_ids.analytic_line_ids'))
        self.assertEqual(len(self.analytic_account.line_ids), 1, "Analytic Account should have only one line")
        self.assertAlmostEqual(self.analytic_account.line_ids[0].amount, -318.18, "Amount on the only AAL is wrong")
        self.assertAlmostEqual(self.analytic_account.line_ids[0].currency_id, self.env.company.currency_id, "Currency on the only AAL is wrong")
        self.assertEqual(self.analytic_account.line_ids[0].product_id, self.product_expense, "Product of AAL should be the one from the expense")

    def test_expense_from_email(self):
        user_marc = self.env['res.users'].create({
            'name': 'Marc User',
            'login': 'Marc',
            'email': 'marc.user@example.com',
        })
        self.env['hr.employee'].create({
            'name': 'Marc Demo',
            'user_id': user_marc.id,
        })
        air_ticket = self.env['product.product'].create({
            'name': 'Air Flight',
            'type': 'service',
            'default_code': 'TESTREF',
            'can_be_expensed': True,
        })

        self.tax.price_include = False

        message_parsed = {
            'message_id': 'the-world-is-a-ghetto',
            'subject': 'TESTREF 9876',
            'email_from': 'marc.user@example.com',
            'to': 'catchall@yourcompany.com',
            'body': "Don't you know, that for me, and for you",
            'attachments': [],
        }

        expense = self.env['hr.expense'].message_new(message_parsed)

        self.assertEqual(expense.product_id, air_ticket)
        self.assertEqual(expense.tax_ids.ids, [])
        self.assertEqual(expense.total_amount, 9876.0)
        self.assertTrue(expense.employee_id in user_marc.employee_ids)

    def test_expense_from_email_without_product(self):
        user_marc = self.env['res.users'].create({
            'name': 'Marc User',
            'login': 'Marc',
            'email': 'marc.user@example.com',
        })
        self.env['hr.employee'].create({
            'name': 'Marc Demo',
            'user_id': user_marc.id,
        })

        self.tax.price_include = False

        message_parsed = {
            'message_id': 'the-world-is-a-ghetto',
            'subject': 'no product code 9876',
            'email_from': 'marc.user@example.com',
            'to': 'catchall@yourcompany.com',
            'body': "Don't you know, that for me, and for you",
            'attachments': [],
        }

        expense = self.env['hr.expense'].message_new(message_parsed)

        self.assertFalse(expense.product_id, "No product should be linked")
        self.assertEqual(expense.tax_ids.ids, [])
        self.assertEqual(expense.total_amount, 9876.0)
        self.assertTrue(expense.employee_id in user_marc.employee_ids)

    def test_partial_payment_multiexpense(self):
        bank_journal = self.env['account.journal'].create({
            'name': 'Payment Journal',
            'code': 'PAY',
            'type': 'bank',
            'company_id': self.env.company.id,
        })

        outbound_pay_method = self.env['account.payment.method'].create({
            'name': 'outbound',
            'code': 'out',
            'payment_type': 'outbound',
        })

        expense = self.env['hr.expense.sheet'].create({
            'name': 'Expense for John Smith',
            'employee_id': self.employee.id,
        })
        expense_line = self.env['hr.expense'].create({
            'name': 'Car Travel Expenses',
            'employee_id': self.employee.id,
            'product_id': self.product_expense.id,
            'unit_amount': 200.00,
            'tax_ids': [(6, 0, [self.tax.id])],
            'sheet_id': expense.id,
            'analytic_account_id': self.analytic_account.id,
        })
        expense_line.copy({
            'sheet_id': expense.id
        })
        expense.approve_expense_sheets()
        expense.action_sheet_move_create()

        exp_move_lines = expense.account_move_id.line_ids
        payable_move_lines = exp_move_lines.filtered(lambda l: l.account_id.internal_type == 'payable')
        self.assertEqual(len(payable_move_lines), 2)

        WizardRegister = self.env["hr.expense.sheet.register.payment.wizard"].with_context(
            active_model=expense._name, active_id=expense.id, active_ids=expense.ids
        )

        register_pay1 = WizardRegister.create({
            'journal_id': bank_journal.id,
            'payment_method_id': outbound_pay_method.id,
            'amount': 300,
        })
        register_pay1.expense_post_payment()

        exp_move_lines = expense.account_move_id.line_ids
        payable_move_lines = exp_move_lines.filtered(lambda l: l.account_id.internal_type == 'payable')
        self.assertEqual(len(payable_move_lines.filtered(lambda l: l.reconciled)), 1)

        register_pay2 = WizardRegister.create({
            'journal_id': bank_journal.id,
            'payment_method_id': outbound_pay_method.id,
            'amount': 100,
        })
        register_pay2.expense_post_payment()
        exp_move_lines = expense.account_move_id.line_ids
        payable_move_lines = exp_move_lines.filtered(lambda l: l.account_id.internal_type == 'payable')
        self.assertEqual(len(payable_move_lines.filtered(lambda l: l.reconciled)), 2)

        full_reconcile = payable_move_lines.mapped('full_reconcile_id')
        self.assertEqual(len(full_reconcile), 1)


class TestExpenseRights(TestExpenseCommon):

    @classmethod
    def setUpClass(cls):
        super(TestExpenseRights, cls).setUpClass()

    def test_expense_create(self):
        # Employee should be able to create an Expense
        self.env['hr.expense'].with_user(self.user_employee).create({
            'name': 'Batmobile repair',
            'employee_id': self.employee.id,
            'product_id': self.product_1.id,
            'unit_amount': 1,
            'quantity': 1,
        })

        # Employee should not be able to create an Expense for someone else
        with self.assertRaises(AccessError):
            self.env['hr.expense'].with_user(self.user_employee).create({
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
            sheet.with_user(self.user_officer).approve_expense_sheets()
        # Officer should not be able to approve own expense sheet
        with self.assertRaises(UserError):
            sheet.with_user(self.user_officer).approve_expense_sheets()
        sheet.with_user(self.user_manager).approve_expense_sheets()

        # Officer should be able to approve expense from his department
        sheet_2.with_user(self.user_officer).approve_expense_sheets()

        # Officer should not be able to approve expense sheet from another department
        with self.assertRaises(AccessError):
            sheet_3.with_user(self.user_officer).approve_expense_sheets()
        sheet_3.with_user(self.user_manager).approve_expense_sheets()

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

        sheet.with_user(self.user_manager).approve_expense_sheets()
        sheet_2.with_user(self.user_manager).approve_expense_sheets()
        sheet_3.with_user(self.user_manager).approve_expense_sheets()

        # Employee should not be able to refuse expense sheet
        with self.assertRaises(UserError):
            sheet.with_user(self.user_employee).refuse_sheet('')
        # Officer should not be able to refuse own expense sheet
        with self.assertRaises(UserError):
            sheet.with_user(self.user_officer).refuse_sheet('')
        sheet.with_user(self.user_manager).refuse_sheet('')

        # Officer should be able to refuse expense from his department
        sheet_2.with_user(self.user_officer).refuse_sheet('')

        # Officer should not be able to refuse expense sheet from another department
        with self.assertRaises(AccessError):
            sheet_3.with_user(self.user_officer).refuse_sheet('')
        sheet_3.with_user(self.user_manager).refuse_sheet('')
