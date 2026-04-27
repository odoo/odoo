#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_work_entry_contract_attendance.tests.common import HrWorkEntryAttendanceCommon

from datetime import datetime, date

from odoo.tests import tagged

@tagged('-at_install', 'post_install', 'payslip_overtime')
class TestPayslipOvertime(HrWorkEntryAttendanceCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.struct_type = cls.env['hr.payroll.structure.type'].create({
            'name': 'Test Structure Type',
            'wage_type': 'hourly',
        })
        cls.struct = cls.env['hr.payroll.structure'].create({
            'name': 'Test Structure - Worker',
            'type_id': cls.struct_type.id,
        })
        cls.payslip = cls.env['hr.payslip'].create({
            'name': 'Test Payslip',
            'employee_id': cls.employee.id,
            'struct_id': cls.struct.id,
            'date_from': '2022-1-1',
            'date_to': '2022-1-31',
        })
        cls.contract.structure_type_id = cls.struct_type
        cls.contract.hourly_wage = 100
        cls.company = cls.payslip.company_id
        
    def test_overtime_outside_period(self):
        # Right before the payslip period
        self.env['hr.attendance.overtime'].create({
            'employee_id': self.employee.id,
            'date': date(2021, 12, 31),
            'duration': 5,
        })
        # Right after the payslip period
        self.env['hr.attendance.overtime'].create({
            'employee_id': self.employee.id,
            'date': date(2022, 2, 1),
            'duration': 5,
        })
        # Since contract resource_calendar_id's default to the company's,
        # we can just change the company's resource_calendar_id's timezone.
        self.env.company.resource_calendar_id.tz = "Asia/Manila"
        self.payslip._compute_worked_days_line_ids()
        self.assertFalse(self.payslip.worked_days_line_ids.filtered(lambda w: w.code == 'OVERTIME'))
        self.env.company.resource_calendar_id.tz = "Indian/Maldives"
        self.payslip._compute_worked_days_line_ids()
        self.assertFalse(self.payslip.worked_days_line_ids.filtered(lambda w: w.code == 'OVERTIME'))
        self.env.company.resource_calendar_id.tz = "Europe/Brussels"
        self.payslip._compute_worked_days_line_ids()
        self.assertFalse(self.payslip.worked_days_line_ids.filtered(lambda w: w.code == 'OVERTIME'))

    def test_with_overtime(self):
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 1, 3, 0, 0, 0),
            'check_out': datetime(2022, 1, 3, 20, 0, 0),
        })
        self.payslip._compute_worked_days_line_ids()
        self.assertEqual(self.payslip.worked_days_line_ids.filtered(lambda w: w.code == 'OVERTIME').number_of_hours, 11)

    def test_with_negative_overtime(self):
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 1, 3, 9, 0, 0),
            'check_out': datetime(2022, 1, 3, 12, 0, 0),
        })
        self.payslip._compute_worked_days_line_ids()
        self.assertFalse(self.payslip.worked_days_line_ids.filtered(lambda w: w.code == 'OVERTIME'))

    def test_with_overtime_calendar_contract(self):
        self.contract.work_entry_source = 'calendar'
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 1, 3, 0, 0, 0),
            'check_out': datetime(2022, 1, 3, 20, 0, 0),
        })
        self.payslip._compute_worked_days_line_ids()
        self.assertEqual(self.payslip.worked_days_line_ids.filtered(lambda w: w.code == 'OVERTIME').number_of_hours, 11)

    def test_overtime_parameter_percent(self):
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 1, 3, 0, 0, 0),
            'check_out': datetime(2022, 1, 3, 20, 0, 0),
        })
        rule_value = self.env.ref('hr_payroll_attendance.rule_parameter_overtime_pay_value')

        rule_value.parameter_value = '50'
        self.payslip._compute_worked_days_line_ids()
        overtime_worked_days = self.payslip.worked_days_line_ids.filtered(lambda w: w.code == 'OVERTIME')
        self.assertEqual(overtime_worked_days.number_of_hours * self.contract.hourly_wage * 0.5, overtime_worked_days.amount)

        rule_value.parameter_value = '100'
        self.env.registry.clear_cache()
        self.payslip._compute_worked_days_line_ids()
        overtime_worked_days = self.payslip.worked_days_line_ids.filtered(lambda w: w.code == 'OVERTIME')
        self.assertEqual(overtime_worked_days.number_of_hours * self.contract.hourly_wage * 1, overtime_worked_days.amount)

        rule_value.parameter_value = '15'
        self.env.registry.clear_cache()
        self.payslip._compute_worked_days_line_ids()
        overtime_worked_days = self.payslip.worked_days_line_ids.filtered(lambda w: w.code == 'OVERTIME')
        self.assertEqual(overtime_worked_days.number_of_hours * self.contract.hourly_wage * .15, overtime_worked_days.amount)

    def test_overtime_with_approval(self):
        """Test that the overtime is taken into account only when it's approved."""
        self.company.write({
            "attendance_overtime_validation": "by_manager"
        })

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 1, 3, 0, 0, 0),
            'check_out': datetime(2022, 1, 3, 20, 0, 0),
        })
        self.payslip._compute_worked_days_line_ids()
        self.assertFalse(self.payslip.worked_days_line_ids.filtered(lambda w: w.code == 'OVERTIME'))

        # Approve the overtime
        attendance.update({
            'overtime_status': 'approved',
        })
        self.payslip._compute_worked_days_line_ids()
        self.assertTrue(self.payslip.worked_days_line_ids.filtered(lambda w: w.code == 'OVERTIME'))

        # refuse the overtime
        attendance.update({
            'overtime_status': 'refused',
        })
        self.payslip._compute_worked_days_line_ids()
        self.assertFalse(self.payslip.worked_days_line_ids.filtered(lambda w: w.code == 'OVERTIME'))
