# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource


class TestCheckJournalEntry(TransactionCase):
    """
    Check journal entries when the expense product is having tax which is tax included.
    """

    def setUp(self):
        super(TestCheckJournalEntry, self).setUp()

        self.Expense = self.env['hr.expense']
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

        self.expense = self.env['hr.expense.sheet'].create({
            'name': 'Expense for John Smith',
            'employee_id': self.employee.id,
        })
        self.expense_line = self.Expense.create({
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

    def test_expense_email_message(self):
        self.Mail = self.env['mail.mail']
        company_email = '\"' + self.env.user.company_id.name + \
                        '\" <' + self.env.user.company_id.email + '>'
        # Mail script will fetch request and process it after reading file.
        request_file = open(get_module_resource('hr_expense', 'tests', 'expense_request.eml'), 'rb')
        request_message = request_file.read()
        self.env['mail.thread'].message_process('hr.expense', request_message)
        # After processing file, expense is created.
        expense = self.Expense.search(['|',
                                      ('employee_id.work_email', 'ilike', 'demo@yourcompany.example.com'),
                                      ('employee_id.user_id.email', 'ilike', 'demo@yourcompany.example.com')], 
                                      limit=1)
        self.assertTrue(expense.ids, 'No expense recorded.')
        # Mail record is created to notify sender, that his/her expense is created successfully
        outgoing_mail = self.Mail.search([
                            ('mail_message_id', 'in', expense.message_ids.ids),
                            ('state', '=', 'sent')])
        self.assertTrue(outgoing_mail.email_from, company_email)
        self.assertTrue(outgoing_mail.state, 'sent')  # Check for mail status
