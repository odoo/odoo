# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime

from odoo.tests import new_test_user
from odoo.tests.common import tagged, TransactionCase

@tagged('post_install', '-at_install', 'hr_attendance_overtime')
class TestHrAttendanceOvertime(TransactionCase):
    """ Tests for overtime """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'SweatChipChop Inc.',
            'hr_attendance_overtime': True,
            'overtime_start_date': datetime(2021, 1, 1),
            'overtime_company_threshold': 10,
            'overtime_employee_threshold': 10,
        })
        cls.company.resource_calendar_id.tz = 'Europe/Brussels'
        cls.company_1 = cls.env['res.company'].create({
            'name': 'Overtime Inc.',
            'hr_attendance_overtime': True,
            'overtime_start_date': datetime(2024, 5, 27),
        })
        cls.company_1.resource_calendar_id.tz = 'Europe/Brussels'
        cls.user = new_test_user(cls.env, login='fru', groups='base.group_user,hr_attendance.group_hr_attendance_manager', company_id=cls.company.id).with_company(cls.company)
        cls.employee = cls.env['hr.employee'].create({
            'name': "Marie-Edouard De La Court",
            'user_id': cls.user.id,
            'company_id': cls.company.id,
            'tz': 'UTC',
        })
        cls.other_employee = cls.env['hr.employee'].create({
            'name': 'Yolanda',
            'company_id': cls.company.id,
            'tz': 'UTC',
        })
        cls.jpn_employee = cls.env['hr.employee'].create({
            'name': 'Sacha',
            'company_id': cls.company.id,
            'tz': 'Asia/Tokyo',
        })
        cls.honolulu_employee = cls.env['hr.employee'].create({
            'name': 'Susan',
            'company_id': cls.company.id,
            'tz': 'Pacific/Honolulu',
        })
        cls.europe_employee = cls.env['hr.employee'].with_company(cls.company_1).create({
            'name': 'Schmitt',
            'company_id': cls.company_1.id,
            'tz': 'Europe/Brussels',
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
        self.assertEqual(overtime.duration, 0, 'Overtime duration should be 0 when an attendance has not been checked out.')
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
            'check_out': datetime(2021, 1, 4, 17, 0)
        })
        self.assertEqual(self.employee.total_overtime, 12)

        attendance.unlink()
        self.assertEqual(self.employee.total_overtime, 1)

    def test_overtime_change_employee(self):
        Attendance = self.env['hr.attendance']
        attendance = Attendance.create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 7, 0),
            'check_out': datetime(2021, 1, 4, 18, 0)
        })
        self.assertEqual(self.employee.total_overtime, 2)
        self.assertEqual(self.other_employee.total_overtime, 0)

        Attendance.create({
            'employee_id': self.other_employee.id,
            'check_in': datetime(2021, 1, 4, 7, 0),
            'check_out': datetime(2021, 1, 4, 18, 0)
        })
        attendance.unlink()
        self.assertEqual(self.other_employee.total_overtime, 2)
        self.assertEqual(self.employee.total_overtime, 0)

    def test_overtime_far_timezones(self):
        # Since dates have to be stored in utc these are the tokyo timezone times for 7-12 / 13-18 (UTC+9)
        self.env['hr.attendance'].create({
            'employee_id': self.jpn_employee.id,
            'check_in': datetime(2021, 1, 3, 22, 0),
            'check_out': datetime(2021, 1, 4, 9, 0),
        })
        # Same but for alaskan times (UTC-10)
        self.env['hr.attendance'].create({
            'employee_id': self.honolulu_employee.id,
            'check_in': datetime(2021, 1, 4, 17, 0),
            'check_out': datetime(2021, 1, 5, 4, 0),
        })
        self.assertEqual(self.jpn_employee.total_overtime, 2)
        self.assertEqual(self.honolulu_employee.total_overtime, 2)

    def test_overtime_unclosed(self):
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 8, 0),
        })
        overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id)])
        self.assertFalse(overtime, 'Overtime entry should not exist at this point.')
        # Employees goes to eat
        attendance.write({
            'check_out': datetime(2021, 1, 4, 12, 0),
        })
        overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id)])
        self.assertTrue(overtime, 'An overtime entry should have been created.')
        self.assertEqual(overtime.duration, -4, 'User still has to work the afternoon.')

        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 13, 0),
        })
        self.assertEqual(overtime.duration, 0, 'Overtime entry has been reset due to an unclosed attendance.')

    def test_overtime_company_threshold(self):
        self.env['hr.attendance'].create([
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 1, 4, 7, 55),
                'check_out': datetime(2021, 1, 4, 12, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 1, 4, 13, 0),
                'check_out': datetime(2021, 1, 4, 17, 5),
            }
        ])
        overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id)])
        self.assertFalse(overtime, 'No overtime should be counted because of the threshold.')

        self.company.write({
            'hr_attendance_overtime': True,
            'overtime_start_date': date(2021, 1, 1),
            'overtime_company_threshold': 4,
        })

        overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id)])
        self.assertTrue(overtime, 'Overtime entry should exist since the threshold has been lowered.')
        self.assertAlmostEqual(overtime.duration, 10 / 60, msg='Overtime should be equal to 10 minutes.')

    def test_overtime_employee_threshold(self):
        self.env['hr.attendance'].create([
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 1, 4, 8, 5),
                'check_out': datetime(2021, 1, 4, 12, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 1, 4, 13, 0),
                'check_out': datetime(2021, 1, 4, 16, 55),
            }
        ])

        overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id)])
        self.assertFalse(overtime, 'No overtime should be counted because of the threshold.')

        self.company.write({
            'hr_attendance_overtime': True,
            'overtime_start_date': date(2021, 1, 1),
            'overtime_employee_threshold': 4,
        })

        overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id)])
        self.assertTrue(overtime, 'Overtime entry should exist since the threshold has been lowered.')
        self.assertAlmostEqual(overtime.duration, -(10 / 60), msg='Overtime should be equal to -10 minutes.')

    def test_overtime_both_threshold(self):
        self.env['hr.attendance'].create([
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 1, 4, 8, 5),
                'check_out': datetime(2021, 1, 4, 12, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 1, 4, 13, 0),
                'check_out': datetime(2021, 1, 4, 17, 5),
            }
        ])

        overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id)])
        self.assertFalse(overtime, 'No overtime should be counted because of the threshold.')

        self.company.write({
            'hr_attendance_overtime': True,
            'overtime_start_date': date(2021, 1, 1),
            'overtime_employee_threshold': 4,
        })

        overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id)])
        self.assertTrue(overtime, 'Overtime entry should exist since the employee threshold has been lowered.')
        self.assertAlmostEqual(overtime.duration, -(5 / 60), msg='Overtime should be equal to -5 minutes.')

        self.company.write({
            'hr_attendance_overtime': True,
            'overtime_start_date': date(2021, 1, 1),
            'overtime_company_threshold': 4,
        })

        overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id)])
        self.assertFalse(overtime, 'Overtime entry should be unlinked since both overtime cancel each other.')

    def test_overtime_lunch(self):
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 8, 0),
            'check_out': datetime(2021, 1, 4, 17, 0),
        })
        self.assertEqual(self.employee.total_overtime, 0, 'There should be no overtime since the employee worked through the lunch period.')

        # check that no overtime is created when employee starts and finishes 1 hour earlier but works through lunch period
        attendance.check_in = datetime(2021, 1, 4, 7, 0)
        attendance.check_out = datetime(2021, 1, 4, 16, 0)
        self.assertEqual(self.employee.total_overtime, 0, 'There should be no overtime since the employee worked through the lunch period.')

        # same but for 1 hour later
        attendance.check_in = datetime(2021, 1, 4, 9, 0)
        attendance.check_out = datetime(2021, 1, 4, 18, 0)
        self.assertEqual(self.employee.total_overtime, 0, 'There should be no overtime since the employee worked through the lunch period.')

    def test_overtime_hours_inside_attendance(self):
        # 1 Attendance case
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2023, 1, 2, 8, 0),
            'check_out': datetime(2023, 1, 2, 21, 0)
        })

        # 8:00 -> 21:00 should contain 4 hours of overtime
        self.assertAlmostEqual(attendance.overtime_hours, 4, 2)

        # Total overtime for that day : 4 hours
        overtime_1 = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id),
                                                              ('date', '=', datetime(2023, 1, 2))])
        self.assertAlmostEqual(overtime_1.duration, 4, 2)

        # Multi attendance case

        m_attendance_1 = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2023, 1, 3, 8, 0),
            'check_out': datetime(2023, 1, 3, 19, 0)
        })
        # 8:00 -> 19:00 should contain 2 hours of overtime
        self.assertAlmostEqual(m_attendance_1.overtime_hours, 2, 2)

        m_attendance_2 = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2023, 1, 3, 19, 0),
            'check_out': datetime(2023, 1, 3, 20, 0)
        })
        # 19:00 -> 20:00 should contain 1 hour of overtime
        self.assertAlmostEqual(m_attendance_2.overtime_hours, 1, 2)

        m_attendance_3 = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2023, 1, 3, 21, 0),
            'check_out': datetime(2023, 1, 3, 23, 0)
        })
        # 21:00 -> 23:00 should contain 2 hours of overtime
        self.assertAlmostEqual(m_attendance_3.overtime_hours, 2, 2)

        overtime_2 = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id),
                                                                ('date', '=', datetime(2023, 1, 3))])
        # Total overtime for that day : 5 hours
        self.assertEqual(overtime_2.duration, 5)

        # Attendance Modification case

        m_attendance_3.write({
            'check_out': datetime(2023, 1, 3, 22, 30)
        })

        self.assertEqual(m_attendance_3.overtime_hours, 1.5)

        # Deleting previous attendances should update correctly the overtime hours in other attendances
        m_attendance_2.unlink()
        m_attendance_1.write({
            'check_out': datetime(2023, 1, 3, 17, 0)
        })
        m_attendance_3.write({
            'check_out': datetime(2023, 1, 3, 21, 30)
        })
        self.assertEqual(m_attendance_3.overtime_hours, 0.5)

        # Create an attendance record for early check-in
        early_attendance = self.env['hr.attendance'].create({
            'employee_id': self.europe_employee.id,
            'check_in': datetime(2024, 5, 27, 23, 30),
            'check_out': datetime(2024, 5, 28, 13, 30)
        })

        # 5:00 -> 19:00[in emp tz] should contain 5 hours of overtime
        self.assertAlmostEqual(early_attendance.overtime_hours, 5)

        # Total overtime for that day : 5 hours
        overtime_record = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.europe_employee.id),
                                                              ('date', '=', datetime(2024, 5, 28))])
        self.assertAlmostEqual(overtime_record.duration, 5)
