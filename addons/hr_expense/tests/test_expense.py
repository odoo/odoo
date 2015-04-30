# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase

class TestExpense(TransactionCase):

    def setUp(self):
        super(TestExpense, self).setUp()

    def test_expense(self):
        expense = self.env['hr.expense'].create({
            'name': 'Expense',
            'employee_id': self.env.ref('hr.employee').id,
            'product_id': self.env.ref('hr_expense.air_ticket').id,
        })

        expense.submit_expenses()
        self.assertEquals(expense.state, 'confirm', "Expense should be in Confirm state.")

        #I approve the expenses sheet.
        expense.approve_expenses()
        expense.expense_id.signal_workflow('validate')
        self.assertEquals(expense.expense_id.state, 'accepted', "Expense sheet should be in accepted state.")

        #Check receipt details.
        expense.expense_id.signal_workflow('done')
        self.assertEquals(expense.expense_id.state, 'done', "Expense sheet should be in done state.")

        #Duplicate the expenses and cancel duplicated.
        duplicate_expense = expense.expense_id.copy()
        duplicate_expense.sheet_cancelled()
        self.assertEquals(duplicate_expense.state, 'cancel', "Expense sheet should be in cancel state.")
