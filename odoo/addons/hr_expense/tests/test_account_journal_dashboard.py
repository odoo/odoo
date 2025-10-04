from odoo.tools.misc import format_amount

from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountJournalDashboard(TestExpenseCommon):

    def test_expense_journal_numbers_and_sums(self):
        journal = self.company_data['default_journal_purchase']
        company_currency = self.env.company.currency_id
        expense_sheet = self.create_expense_report()
        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        expense_sheet.flush_recordset()
        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data['sum_expenses_to_pay'], format_amount(self.env, 1000, company_currency))

        payment = self.get_new_payment(expense_sheet, 250.0)
        expense_sheet.flush_recordset()
        payment.flush_recordset()
        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        # todo master: have 750 (residual amount will be used)
        # we still want to assert a second time in order to make sure that partially paid expenses are displayed
        self.assertEqual(dashboard_data['sum_expenses_to_pay'], format_amount(self.env, 1000, company_currency))
