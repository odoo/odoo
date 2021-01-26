# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime

from odoo.tests import new_test_user
from odoo.tests.common import TransactionCase


class TestHrAttendanceOvertime(TransactionCase):
    """ Tests for overtime """

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({
            'name': 'SweatChopChop Inc.',
            'hr_attendance_overtime': True,
            'overtime_start_date': datetime(2021, 1, 1)
        })
        self.env.company = self.company
        self.user = new_test_user(self.env, login='fru', groups='base.group_user,hr_attendance.group_hr_attendance', company_id=self.company.id)
        self.employee = self.env['hr.employee'].create({
            'name': "Marie-Edouard De La Court",
            'user_id': self.user.id,
            'company_id': self.company.id,
        })
        self.other_employee = self.env['hr.employee'].create({
            'name': 'Yolanda',
            'company_id': self.company.id,
        })

    def test_overtime_company_settings(self):
        self.company.hr_attendance_overtime = False

        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 8, 0),
            'check_out': datetime(2021, 1, 4, 20, 0)
        })

        overtime = self.env['hr.attendance.overtime'].search_count([('employee_id', '=', self.employee.id), ('date', '=', date(2021, 1, 4))])
        self.assertFalse(overtime, 'No overtime should be created')

        self.company.write({
            'hr_attendance_overtime': True,
            'overtime_start_date': date(2021, 1, 1)
        })
        overtime = self.env['hr.attendance.overtime'].search_count([('employee_id', '=', self.employee.id), ('date', '=', date(2021, 1, 4))])
        self.assertTrue(overtime, 'Overtime should be created')

        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2020, 12, 30, 8, 0),
            'check_out': datetime(2020, 12, 30, 20, 0)
        })
        overtime = self.env['hr.attendance.overtime'].search_count([('employee_id', '=', self.employee.id), ('date', '=', date(2020, 12, 30))])
        self.assertFalse(overtime, 'No overtime should be created before the start date')

    def test_simple_overtime(self):
        checkin_am = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 8, 0)
        })
        self.env['hr.attendance'].create({
            'employee_id': self.other_employee.id,
            'check_in': datetime(2021, 1, 4, 8, 0),
            'check_out': datetime(2021, 1, 4, 22, 0)
        })

        overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id), ('date', '=', date(2021, 1, 4))])
        self.assertFalse(overtime, 'No overtime record should exist for that employee')

        checkin_am.write({'check_out': datetime(2021, 1, 4, 12, 0)})
        overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id), ('date', '=', date(2021, 1, 4))])
        self.assertTrue(overtime, 'An overtime record should be created')
        self.assertEqual(overtime.duration, -4)

        checkin_pm = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 13, 0)
        })
        self.assertEqual(overtime.duration, -4, 'Overtime duration should not change yet')
        checkin_pm.write({'check_out': datetime(2021, 1, 4, 18, 0)})
        self.assertTrue(overtime.exists(), 'Overtime should not be deleted')
        self.assertAlmostEqual(overtime.duration, 1)
        self.assertAlmostEqual(self.employee.total_overtime, 1)

    def test_overtime_weekend(self):
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 2, 8, 0),
            'check_out': datetime(2021, 1, 2, 11, 0)
        })

        overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id), ('date', '=', date(2021, 1, 2))])
        self.assertTrue(overtime, 'Overtime should be created')
        self.assertEqual(overtime.duration, 3, 'Should have 3 hours of overtime')
        self.assertEqual(self.employee.total_overtime, 3, 'Should still have 3 hours of overtime')

    def test_overtime_multiple(self):
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 2, 8, 0),
            'check_out': datetime(2021, 1, 2, 19, 0)
        })
        self.assertEqual(self.employee.total_overtime, 11)

        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 7, 0),
            'check_out': datetime(2021, 1, 4, 16, 0)
        })
        self.assertEqual(self.employee.total_overtime, 12)

        attendance.unlink()
        self.assertEqual(self.employee.total_overtime, 1)

    def test_overtime_change_employee(self):
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 7, 0),
            'check_out': datetime(2021, 1, 4, 18, 0)
        })
        self.assertEqual(self.employee.total_overtime, 3)
        self.assertEqual(self.other_employee.total_overtime, 0)

        attendance.employee_id = self.other_employee.id
        self.assertEqual(self.other_employee.total_overtime, 3)
        self.assertEqual(self.employee.total_overtime, -8)
