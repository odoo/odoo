from datetime import datetime

from odoo.addons.hr_payroll.tests.common import TestPayslipBase
from odoo.tests.common import tagged


@tagged('-at_install', 'post_install_l10n', 'post_install')
class TestPayrollWorkedDays(TestPayslipBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        mexico = cls.env.ref('base.mx')
        cls.env.company.write({
            'country_id': mexico.id
        })
        cls.richard_emp.write({
            'company_id': cls.env.company,
            'country_id': mexico.id,
        })
        sw_structure = cls.env['hr.payroll.structure.type'].create({
            'name': 'Software Developer'
        })
        developer_pay_structure = cls.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for Software Developer',
            'type_id': sw_structure.id,
            'unpaid_work_entry_type_ids': [(4, cls.work_entry_type_unpaid.id, False)],
        })
        cls.richard_emp.contract_ids.write({
            'date_end': datetime(2050, 1, 1),
        })
        cls.payslip = cls.env['hr.payslip'].create({
            'name': 'Payslip of Richard Quarter',
            'employee_id': cls.richard_emp.id,
            'contract_id': cls.richard_emp.contract_ids[0].id,
            'struct_id': developer_pay_structure.id,
            'date_from': datetime(2030, 1, 1).date(),
            'date_to': datetime(2030, 2, 1).date(),
        })
        cls.richard_emp.contract_ids[0].wage = 5000

    def _reset_work_entries(self, contract):
        self.env['hr.work.entry'].search([('employee_id', '=', contract.employee_id.id)]).unlink()
        now = datetime(2030, 1, 1, 0, 0, 0)
        contract.write({
            'date_generated_from': now,
            'date_generated_to': now,
        })

    def test_monthly_payslip(self):
        self._reset_work_entries(self.richard_emp.contract_ids)
        amount_to_be_paid = sum(line.amount for line in self.payslip.worked_days_line_ids)
        self.assertEqual(amount_to_be_paid, 5000)
        self.env['resource.calendar.leaves'].create({
            'name': 'Doctor Appointment',
            'date_from': datetime.strptime('2030-1-1 07:00:00', '%Y-%m-%d %H:%M:%S'),
            'date_to': datetime.strptime('2030-1-16 18:00:00', '%Y-%m-%d %H:%M:%S'),
            'resource_id': self.richard_emp.resource_id.id,
            'calendar_id': self.richard_emp.resource_calendar_id.id,
            'work_entry_type_id': self.work_entry_type_unpaid.id,
            'time_type': 'leave',
        })
        self.payslip._compute_worked_days_line_ids()
        amount_to_be_paid = sum(line.amount for line in self.payslip.worked_days_line_ids)
        self.assertAlmostEqual(amount_to_be_paid, 2500, places=2)

    def test_hourly_payslip(self):
        self._reset_work_entries(self.richard_emp.contract_ids)
        self.richard_emp.contract_ids.wage_type = 'hourly'
        self.richard_emp.contract_ids.hourly_wage = 20
        self.payslip._compute_worked_days_line_ids()
        amount_to_be_paid = sum(line.amount for line in self.payslip.worked_days_line_ids)
        self.assertEqual(amount_to_be_paid, 3840)
        self.env['resource.calendar.leaves'].create({
            'name': 'Doctor Appointment',
            'date_from': datetime.strptime('2030-1-1 07:00:00', '%Y-%m-%d %H:%M:%S'),
            'date_to': datetime.strptime('2030-1-16 18:00:00', '%Y-%m-%d %H:%M:%S'),
            'resource_id': self.richard_emp.resource_id.id,
            'calendar_id': self.richard_emp.resource_calendar_id.id,
            'work_entry_type_id': self.work_entry_type_unpaid.id,
            'time_type': 'leave',
        })
        self._reset_work_entries(self.richard_emp.contract_ids)
        self.payslip._compute_worked_days_line_ids()
        amount_to_be_paid = sum(line.amount for line in self.payslip.worked_days_line_ids)
        self.assertEqual(amount_to_be_paid, 1920)
