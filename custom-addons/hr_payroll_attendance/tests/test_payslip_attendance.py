# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_work_entry_contract_attendance.tests.common import HrWorkEntryAttendanceCommon

from datetime import datetime

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
