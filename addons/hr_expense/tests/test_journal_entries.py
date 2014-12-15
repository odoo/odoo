# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase

class TestCheckJournalEntry(TransactionCase):
    """
    Check journal entries when the expense product is having tax which is tax included.
    """

    def setUp(self):
        super(TestCheckJournalEntry, self).setUp()

    def test_journal_entry(self):
        base_code = self.env['account.tax.code'].create({'name': 'Expense Base Code'})

        tax = self.env['account.tax'].create({
            'name': 'Expense 10%',
            'amount': 0.10,
            'type': 'percent',
            'type_tax_use': 'purchase',
            'price_include': True,
            'base_code_id': base_code.id,
            'base_sign': -1,
        })

        expense = self.env['hr.expense'].create({
            'name': 'Car Travel Expenses',
            'product_id': self.env.ref('hr_expense.air_ticket').id,
            'unit_amount': 700.00,
            'expense_tax_id': [(6, 0, tax.ids)],
        })

        expense.submit_expenses()
        self.assertEquals(expense.state, 'confirm', "Expense should be in Confirm state.")

        #Submit to Manager
        expense.approve_expenses()
        #Approve
        expense.expense_id.signal_workflow('validate')
        #Create Expense Entries
        expense.expense_id.signal_workflow('done')
        self.assertEquals(expense.expense_id.state, 'done', 'Expense is not in Waiting Payment state')
        self.assertTrue(expense.expense_id.account_move_id.id, 'Expense Journal Entry is not created')
        for line in expense.expense_id.account_move_id.line_id:
            if line.credit:
                self.assertEquals(line.credit, 700.00, 'Expense Payable Amount is not matched for journal item')
            else:
                if line.tax_code_id:
                    self.assertEquals(line.debit, 636.36, 'Tax Amount is not matched for journal item')
                else:
                    self.assertEquals(line.debit, 63.64, 'Tax Base Amount is not matched for journal item')
