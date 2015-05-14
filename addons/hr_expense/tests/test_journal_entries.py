from openerp.tests.common import TransactionCase
from openerp import workflow


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
        _, self.product_id = self.registry("ir.model.data").get_object_reference(cr, uid, "hr_expense", "air_ticket")
        self.employee = self.registry("ir.model.data").xmlid_to_object(cr, uid, "hr.employee_mit")
        self.tax_id = self.tax_obj.create(cr, uid, {
            'name': 'Expense 10%',
            'amount': 10,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'price_include': True,
        })
        self.product_obj.write(cr, uid, self.product_id, {'supplier_taxes_id': [(6, 0, [self.tax_id])]})
        # Create payable account for the expense
        user_type_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'account', 'data_account_type_payable')[1]
        account_payable_id = self.registry('account.account').create(cr, uid, {'code': 'X1111', 'name': 'HR Expense - Test Payable Account', 'user_type_id': user_type_id, 'reconcile': True})
        # Create expenses account for the expense
        user_type_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'account', 'data_account_type_expenses')[1]
        account_expense_id = self.registry('account.account').create(cr, uid, {'code': 'X2120', 'name': 'HR Expense - Test Purchase Account', 'user_type_id': user_type_id})
        # Assign it to the air ticket product
        self.registry('product.product').write(cr, uid, self.product_id, {'property_account_expense_id': account_expense_id})
        # Create Sale Journal
        company_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'main_company')[1]
        self.registry('account.journal').create(cr, uid, {'name': 'Purchase Journal - Test', 'code': 'HRTPJ', 'type': 'purchase', 'company_id': company_id})
        self.expense_id = self.expense_obj.create(cr, uid, {
            'name': 'Expense for Minh Tran',
            'employee_id': self.employee.id,
            'employee_payable_account_id': account_payable_id,
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
        for line in self.expense.account_move_id.line_ids:
            if line.credit:
                self.assertAlmostEquals(line.credit, 700.00)
            else:
                if not line.tax_line_id.id == self.tax_id:
                    self.assertAlmostEquals(line.debit, 636.36)
                else:
                    self.assertAlmostEquals(line.debit, 63.64)
