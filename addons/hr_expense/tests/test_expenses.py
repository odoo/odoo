# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestCheckJournalEntry(TransactionCase):
    """
    Check journal entries when the expense product is having tax which is tax included.
    """

    def setUp(self):
        super(TestCheckJournalEntry, self).setUp()

        self.tax = self.env['account.tax'].create({
            'name': 'Expense 10%',
            'amount': 10,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'price_include': True,
        })
        self.product = self.env.ref('hr_expense.air_ticket')
        self.product.write({'supplier_taxes_id': [(6, 0, [self.tax.id])]})

        self.employee = self.env.ref('hr.employee_mit')

        # Create payable account for the expense
        user_type = self.env.ref('account.data_account_type_payable')
        account_payable = self.env['account.account'].create({
            'code': 'X1111',
            'name': 'HR Expense - Test Payable Account',
            'user_type_id': user_type.id,
            'reconcile': True
        })
        self.employee.address_home_id.property_account_payable_id = account_payable.id

        # Create expenses account for the expense
        user_type = self.env.ref('account.data_account_type_expenses')
        account_expense = self.env['account.account'].create({
            'code': 'X2120',
            'name': 'HR Expense - Test Purchase Account',
            'user_type_id': user_type.id
        })
        # Assign it to the air ticket product
        self.product.write({'property_account_expense_id': account_expense.id})

        # Create Sales Journal
        company = self.env.ref('base.main_company')
        self.env['account.journal'].create({
            'name': 'Purchase Journal - Test',
            'code': 'HRTPJ',
            'type': 'purchase',
            'company_id': company.id
        })

        self.bank_journal = self.env['account.journal'].create({
            'name': 'Payment Journal',
            'code': 'PAY',
            'type': 'bank',
            'company_id': company.id
        })

        self.outbound_pay_method = self.env['account.payment.method'].create({
            'name': 'outbound',
            'code': 'out',
            'payment_type': 'outbound',
        })

        self.expense = self.env['hr.expense.sheet'].create({
            'name': 'Expense for John Smith',
            'employee_id': self.employee.id,
        })
        self.expense_line = self.env['hr.expense'].create({
            'name': 'Car Travel Expenses',
            'employee_id': self.employee.id,
            'product_id': self.product.id,
            'unit_amount': 700.00,
            'tax_ids': [(6, 0, [self.tax.id])],
            'sheet_id': self.expense.id,
        })

    def test_journal_entry(self):
        # Submitted to Manager
        self.assertEquals(self.expense.state, 'submit', 'Expense is not in Reported state')
        # Approve
        self.expense.approve_expense_sheets()
        self.assertEquals(self.expense.state, 'approve', 'Expense is not in Approved state')
        # Create Expense Entries
        self.expense.action_sheet_move_create()
        self.assertEquals(self.expense.state, 'post', 'Expense is not in Waiting Payment state')
        self.assertTrue(self.expense.account_move_id.id, 'Expense Journal Entry is not created')

        # [(line.debit, line.credit, line.tax_line_id.id) for line in self.expense.expense_line_ids.account_move_id.line_ids]
        # should git this result [(0.0, 700.0, False), (63.64, 0.0, 179), (636.36, 0.0, False)]
        for line in self.expense.account_move_id.line_ids:
            if line.credit:
                self.assertAlmostEquals(line.credit, 700.00)
            else:
                if not line.tax_line_id == self.tax:
                    self.assertAlmostEquals(line.debit, 636.36)
                else:
                    self.assertAlmostEquals(line.debit, 63.64)

    def test_expense_from_email(self):
        user_demo = self.env.ref('base.user_demo')
        self.tax.price_include = False

        message_parsed = {
            'message_id': 'the-world-is-a-ghetto',
            'subject': '[AT] 9876',
            'email_from': 'demo@yourcompany.example.com',
            'to': 'catchall@yourcompany.com',
            'body': "Don't you know, that for me, and for you",
            'attachments': [],
        }

        expense = self.env['hr.expense'].message_new(message_parsed)

        self.assertEquals(expense.product_id, self.product)
        self.assertEquals(expense.tax_ids.ids, [self.tax.id])
        self.assertEquals(expense.total_amount, 10863.60)
        self.assertTrue(expense.employee_id in user_demo.employee_ids)

    def test_partial_payment_multiexpense(self):
        self.expense_line.unit_amount = 200
        expense_line2 = self.expense_line.copy({
            'sheet_id': self.expense.id
        })
        self.expense.approve_expense_sheets()
        self.expense.action_sheet_move_create()
        exp_move_lines = self.expense.account_move_id.line_ids
        payable_move_lines = exp_move_lines.filtered(lambda l: l.account_id.internal_type == 'payable')
        self.assertEquals(len(payable_move_lines), 2)

        WizardRegister = self.env['hr.expense.sheet.register.payment.wizard'].with_context(active_ids=self.expense.ids)

        register_pay1 = WizardRegister.create({
            'journal_id': self.bank_journal.id,
            'payment_method_id': self.outbound_pay_method.id,
            'amount': 300,
        })
        register_pay1.expense_post_payment()

        exp_move_lines = self.expense.account_move_id.line_ids
        payable_move_lines = exp_move_lines.filtered(lambda l: l.account_id.internal_type == 'payable')
        self.assertEquals(len(payable_move_lines.filtered(lambda l: l.reconciled)), 1)

        register_pay2 = WizardRegister.create({
            'journal_id': self.bank_journal.id,
            'payment_method_id': self.outbound_pay_method.id,
            'amount': 100,
        })
        register_pay2.expense_post_payment()
        exp_move_lines = self.expense.account_move_id.line_ids
        payable_move_lines = exp_move_lines.filtered(lambda l: l.account_id.internal_type == 'payable')
        self.assertEquals(len(payable_move_lines.filtered(lambda l: l.reconciled)), 2)

        full_reconcile = payable_move_lines.mapped('full_reconcile_id')
        self.assertEquals(len(full_reconcile), 1)
