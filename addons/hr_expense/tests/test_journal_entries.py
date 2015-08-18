from openerp.tests.common import TransactionCase
from openerp import netsvc, workflow


class TestCheckJournalEntry(TransactionCase):
    """
    Check journal entries when the expense product is having tax which is tax included. 
    """

    def setUp(self):
        super(TestCheckJournalEntry, self).setUp()
        cr, uid = self.cr, self.uid
        self.expense_obj = self.registry('hr.expense.expense')
        self.exp_line_obj = self.registry('hr.expense.line')
        self.product_obj = self.registry('product.product')
        self.tax_obj = self.registry('account.tax')
        self.code_obj = self.registry('account.tax.code')
        _, self.product_id = self.registry("ir.model.data").get_object_reference(cr, uid, "hr_expense", "air_ticket")
        _, self.employee_id = self.registry("ir.model.data").get_object_reference(cr, uid, "hr", "employee_mit")
        self.base_code_id = self.code_obj.create(cr, uid, {'name': 'Expense Base Code'})
        self.tax_id = self.tax_obj.create(cr, uid, {
            'name': 'Expense 10%',
            'amount': 0.10,
            'type': 'percent',
            'type_tax_use': 'purchase',
            'price_include': True,
            'base_code_id': self.base_code_id,
            'base_sign': -1,
        })
        self.product_obj.write(cr, uid, self.product_id, {'supplier_taxes_id': [(6, 0, [self.tax_id])]})
        self.expense_id = self.expense_obj.create(cr, uid, {
            'name': 'Expense for Minh Tran',
            'employee_id': self.employee_id,
        })
        self.exp_line_obj.create(cr, uid, {
            'name': 'Car Travel Expenses',
            'product_id': self.product_id,
            'unit_amount': 700.00,
            'expense_id': self.expense_id
        })

    def test_journal_entry(self):
        cr, uid = self.cr, self.uid
        #Submit to Manager
        workflow.trg_validate(uid, 'hr.expense.expense', self.expense_id, 'confirm', cr)
        #Approve
        workflow.trg_validate(uid, 'hr.expense.expense', self.expense_id, 'validate', cr)
        #Create Expense Entries
        workflow.trg_validate(uid, 'hr.expense.expense', self.expense_id, 'done', cr)
        self.expense = self.expense_obj.browse(cr, uid, self.expense_id)
        self.assertEquals(self.expense.state, 'done', 'Expense is not in Waiting Payment state')
        self.assertTrue(self.expense.account_move_id.id, 'Expense Journal Entry is not created')
        for line in self.expense.account_move_id.line_id:
            if line.credit:
                self.assertEquals(line.credit, 700.00, 'Expense Payable Amount is not matched for journal item')
            else:
                if line.tax_code_id:
                    self.assertEquals(line.debit, 636.36, 'Tax Amount is not matched for journal item')
                else:
                    self.assertEquals(line.debit, 63.64, 'Tax Base Amount is not matched for journal item')
