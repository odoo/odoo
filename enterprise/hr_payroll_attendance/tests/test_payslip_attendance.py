# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_work_entry_contract_attendance.tests.common import HrWorkEntryAttendanceCommon

from datetime import datetime, date, time
from dateutil.relativedelta import relativedelta

from odoo.tests import tagged

@tagged('-at_install', 'post_install')
class TestPayslipAttendance(HrWorkEntryAttendanceCommon):

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
            'date_from': '2024-1-1',
            'date_to': '2024-1-30',
        })

    def test_get_attendance_from_payslip(self):
        attendance_A, attendance_B, *_ = self.env['hr.attendance'].create([
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2024, 1, 1, 8, 0, 0),
                'check_out': datetime(2024, 1, 1, 16, 0, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2024, 1, 20, 8, 0, 0),
                'check_out': datetime(2024, 1, 20, 16, 0, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2024, 2, 1, 8, 0, 0),
                'check_out': datetime(2024, 2, 1, 16, 0, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2024, 2, 20, 8, 0, 0),
                'check_out': datetime(2024, 2, 20, 16, 0, 0),
            },
        ])
        attendance_by_payslip = self.payslip._get_attendance_by_payslip()
        self.assertEqual(attendance_by_payslip[self.payslip], attendance_A + attendance_B)

    def test_get_attendance_from_payslip_with_timezone(self):
        attendance_A, attendance_B, = self.env['hr.attendance'].create([
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2024, 1, 1, 7, 0, 0),
                'check_out': datetime(2024, 1, 1, 15, 0, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2024, 1, 30, 23, 30, 0), # 2024-1-31 00-30-00 in UTC+1
                'check_out': datetime(2024, 1, 31, 7, 30, 0),
            },
        ])

        # Without using `_get_attendance_by_payslip`
        domain = [
            ('employee_id', '=', self.employee.id),
            ('check_in', '<=', self.payslip.date_to),
            ('check_out', '>=', self.payslip.date_from)
        ]
        attendances = self.env['hr.attendance'].with_context(tz="Europe/Brussels").search(domain)
        self.assertEqual(attendances, attendance_A + attendance_B) # Not correct (`attendance_B` is not in the payslip period)
        # With using `_get_attendance_by_payslip`:
        attendance_by_payslip = self.payslip.with_context(tz="Europe/Brussels")._get_attendance_by_payslip()
        self.assertEqual(attendance_by_payslip[self.payslip], attendance_A) # Correct

    def test_compute_payslip_no_worked_hours(self):
        employee = self.env['hr.employee'].create({'name': 'John'})
        contract = self.env['hr.contract'].create({
            'name': 'Contract for John',
            'wage': 5000,
            'employee_id': employee.id,
            'date_start': date(2024, 10, 1),
            'date_end': date(2024, 10, 31),
            'work_entry_source': 'attendance',
            'structure_type_id': self.struct_type.id,
            'state': 'open',
        })

        payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of John',
            'employee_id': employee.id,
            'contract_id': contract.id,
            'struct_id': self.struct.id,
            'date_from': date(2024, 10, 1),
            'date_to': date(2024, 10, 31)
        })

        payslip.compute_sheet()
        basic_salary_line = payslip.line_ids.filtered_domain([('code', '=', 'BASIC')])
        self.assertAlmostEqual(basic_salary_line.amount, 0.0, 2, 'Basic salary = 0 worked hours * hourly wage = 0')

    def test_fully_flexible_contracts_payslip(self):
        """ Test payslip generation for fully flexible contracts (no working schedule) with attendance-based work entries """

        structure_type = self.env['hr.payroll.structure.type'].create({
            'name': 'Test - Developer',
        })
        developer_pay_structure = self.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for Software Developer',
            'type_id': structure_type.id,
        })
        structure_type.default_struct_id = developer_pay_structure
        attendance_work_entry_type = self.env.ref('hr_work_entry.work_entry_type_attendance')

        # Case 1: contract with no calendar
        employee_with_calendar = self.env['hr.employee'].create({
            'name': 'employee 1',
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
        })

        flexible_contract_1 = self.env['hr.contract'].create({
            'name': 'flexible contract 1',
            'employee_id': employee_with_calendar.id,
            'resource_calendar_id': False,
            'work_entry_source': 'attendance',
            'wage': 5000,
            'structure_type_id': structure_type.id,
            'date_start': date.today() - relativedelta(months=2),
            'state': 'open',
        })

        date_from = date.today()
        date_to = date_from + relativedelta(months=1)

        for day in range(7):
            work_date = date_from + relativedelta(days=day)
            if work_date.weekday() < 5:
                self.env['hr.work.entry'].create({
                    'name': f'attendance {day + 1}',
                    'employee_id': employee_with_calendar.id,
                    'contract_id': flexible_contract_1.id,
                    'work_entry_type_id': attendance_work_entry_type.id,
                    'date_start': datetime.combine(work_date, time(9, 0, 0)),
                    'date_stop': datetime.combine(work_date, time(17, 0, 0)),
                })

        payslip_1 = self.env['hr.payslip'].create({
            'name': "payslip of employee 1",
            'employee_id': employee_with_calendar.id,
            'contract_id': flexible_contract_1.id,
            'date_from': date_from,
            'date_to': date_to,
        })

        payslip_1.compute_sheet()

        self.assertTrue(payslip_1.worked_days_line_ids, 'worked days should be generated for fully flexible contract')
        attendance_line_1 = payslip_1.worked_days_line_ids.filtered(lambda l: l.work_entry_type_id == attendance_work_entry_type)
        self.assertTrue(attendance_line_1, 'attendance worked days should be present')
        self.assertEqual(attendance_line_1.number_of_days, 5, 'payslip should record 5 worked days')
        self.assertEqual(attendance_line_1.number_of_hours, 40, 'payslip should record 40 hours')

        # Case 2: employee with no calendar, contract with no calendar (full flexibility in both)
        employee_no_calendar = self.env['hr.employee'].create({
            'name': 'employee 2',
            'resource_calendar_id': False,
        })

        flexible_contract_2 = self.env['hr.contract'].create({
            'name': 'flexible contract 2',
            'employee_id': employee_no_calendar.id,
            'resource_calendar_id': False,
            'work_entry_source': 'attendance',
            'wage': 6000,
            'structure_type_id': structure_type.id,
            'date_start': date.today() - relativedelta(months=2),
            'state': 'open',
        })

        for day in range(7):
            work_date = date_from + relativedelta(days=day + 10)
            if work_date.weekday() < 5:
                self.env['hr.work.entry'].create({
                    'name': f'Attendance {day + 1}',
                    'employee_id': employee_no_calendar.id,
                    'contract_id': flexible_contract_2.id,
                    'work_entry_type_id': attendance_work_entry_type.id,
                    'date_start': datetime.combine(work_date, time(8, 0, 0)),
                    'date_stop': datetime.combine(work_date, time(16, 0, 0)),
                })

        payslip_2 = self.env['hr.payslip'].create({
            'name': 'payslip 2',
            'employee_id': employee_no_calendar.id,
            'contract_id': flexible_contract_2.id,
            'date_from': date_from,
            'date_to': date_to,
        })

        payslip_2.compute_sheet()

        self.assertTrue(payslip_2.worked_days_line_ids, 'worked days should be generated for fully flexible contract')
        attendance_line_2 = payslip_2.worked_days_line_ids.filtered(lambda l: l.work_entry_type_id == attendance_work_entry_type)
        self.assertTrue(attendance_line_2, 'attendance worked days should be present')
        self.assertGreater(attendance_line_2.number_of_hours, 0, 'payslip record attendance hours')
