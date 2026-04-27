from freezegun import freeze_time
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.addons.hr_payroll_expense.tests.test_payroll_expense import TestPayrollExpense
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPayrollExpenseCornerCases(TestPayrollExpense):
    @freeze_time("2028-09-15")
    def test_create_payslip_through_batch(self):
        """
        Test that when creating several payslips through a batch, with an employee having different contracts overlapping the batch period
        (thus creating two or more payslips for them), any expense that would be reinvoiced in a payslip
         is only accounted for in one and only one payslip.
        """
        # Creating an expense to be reported in the payslip
        expense_sheet = self.create_expense_report({'accounting_date': fields.Date.today()})
        expense_sheet._do_submit()
        expense_sheet._do_approve()
        expense_sheet.action_report_in_next_payslip()

        # Creating a HR Payroll situation where an employee having two contracts overlapping the same month would get two
        # different payslips generated in the same batch
        specific_structure_type = self.expense_hr_structure.type_id.copy()
        specific_structure = self.env['hr.payroll.structure'].create({
            **self.expense_hr_structure.copy_data()[0],
            'name': 'Specific Structure for Expenses',
            'type_id': specific_structure_type.id,
        })
        new_contract_vals = self.expense_employee.contract_ids.copy_data()[0]
        self.expense_employee.contract_ids.write({
            'structure_type_id': specific_structure_type.id,
            'state': 'close',
            'date_end': fields.Date.today() + relativedelta(months=-1),
        })
        new_contract_vals.update({
            'date_start': self.expense_employee.contract_ids[0].date_end + relativedelta(days=1),
            'date_end': fields.Date.today() + relativedelta(years=1),
            'structure_type_id': specific_structure_type.id,
            'state': 'open',
        })
        self.expense_employee.contract_ids.create(new_contract_vals)

        # Create a batch and generate payslips
        payslip_run = self.env['hr.payslip.run'].create({
            'date_start': fields.Date.today() + relativedelta(months=-1, day=1),
            'date_end': fields.Date.today() + relativedelta(months=1, day=31),
            'name': 'Test',
        })
        payslip_employee = self.env['hr.payslip.employees'].create({
            'structure_id': specific_structure.id,
        })
        payslip_employee.with_context(active_id=payslip_run.id).compute_sheet()

        self.assertEqual(
            expense_sheet.total_amount,
            sum(payslip_run.slip_ids.line_ids.filtered(lambda line: line.code == 'EXPENSES').mapped('amount')),
            "The total amount of the expense report should be equal to "
            "the sum of the 'EXPENSES' lines in the payslips created through the batch process."
        )
