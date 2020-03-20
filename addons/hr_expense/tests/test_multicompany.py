# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_expense.tests.common import TestExpenseMultiCompanyCommon
from odoo.tests import tagged

@tagged('post_install','-at_install')
class TestExpenseMultiCompany(TestExpenseMultiCompanyCommon):

    @classmethod
    def setUpClass(cls):
        super(TestExpenseMultiCompany, cls).setUpClass()

        cls.bank_journal = cls.env['account.journal'].create({
            'name': 'Payment Journal',
            'code': 'PAY',
            'type': 'bank',
            'company_id': cls.env.company.id,
        })

        cls.outbound_pay_method = cls.env['account.payment.method'].create({
            'name': 'outbound',
            'code': 'out',
            'payment_type': 'outbound',
        })

    def test_expense_multicompany_company_propagation(self):
        # The company on the expense sheet should be the same as the one from the expense
        expense = self.env['hr.expense.sheet'].create({
            'name': 'Expense for employee a',
            'employee_id': self.employee.id,
            'journal_id': self.sale_journal0.id,
        })

        expense_line = self.env['hr.expense'].create({
            'name': 'Sword Sharpening',
            'employee_id': self.employee.id,
            'product_id': self.product_1.id,
            'unit_amount': 1,
            'quantity': 1,
            'sheet_id': expense.id,
            'analytic_account_id': self.analytic_account.id,
        })

        self.assertEqual(expense_line.company_id.id, self.env.company.id)
        self.assertEqual(expense.company_id.id, self.env.company.id)

        expense.with_context(allowed_company_ids=[self.company_B.id, self.env.company.id], company_id=self.company_B.id).action_submit_sheet()
        self.assertEquals(expense.state, 'submit', 'Expense is not in Reported state')
        self.assertEqual(expense.company_id.id, self.env.company.id)

        expense.with_context(allowed_company_ids=[self.company_B.id, self.env.company.id], company_id=self.company_B.id).approve_expense_sheets()
        self.assertEquals(expense.state, 'approve', 'Expense is not in Approved state')

        expense.with_context(allowed_company_ids=[self.company_B.id, self.env.company.id], company_id=self.company_B.id).action_sheet_move_create()
        self.assertEquals(expense.state, 'post', 'Expense is not in Waiting Payment state')
        self.assertTrue(expense.account_move_id.id, 'Expense Journal Entry is not created')

        exp_move_lines = expense.account_move_id.line_ids
        payable_move_lines = exp_move_lines.filtered(lambda l: l.account_id.internal_type == 'payable')
        self.assertEquals(len(payable_move_lines), 1)
        self.assertEqual(payable_move_lines[0].company_id.id, expense.company_id.id, 'The company of the move line should be the same as the one from the expense.')

        #The company on the payment should be the same as the one on the expense, even if we are in a another company
        WizardRegister = self.env["hr.expense.sheet.register.payment.wizard"].with_context(
            active_model=expense._name, active_id=expense.id, active_ids=expense.ids, allowed_company_ids=[self.company_B.id, self.env.company.id], company_id=self.company_B.id
        )

        register_payement = WizardRegister.create({
            'journal_id': self.bank_journal.id,
            'payment_method_id': self.outbound_pay_method.id,
            'amount': 300,
        })
        self.assertEqual(register_payement.company_id.id, expense.company_id.id, 'The company of the payement should be the same as the one from the expense.')
        register_payement.expense_post_payment()
