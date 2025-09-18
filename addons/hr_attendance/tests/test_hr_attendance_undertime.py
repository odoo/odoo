# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime

from odoo import Command
from odoo.tests import Form, HttpCase, new_test_user
from odoo.tests.common import tagged


@tagged('hr_attendance_overtime')
class TestHrAttendanceUndertime(HttpCase):
    """ Tests for undertime """

    @classmethod
    def setUpClass(cls):
        def set_calendar_and_tz(employee, tz):
            employee.resource_calendar_id = cls.env['resource.calendar'].create({
                'name': f'Default Calendar ({tz})',
                'tz': tz,
            })
        super().setUpClass()

        cls.company = cls.env['res.company'].create({
            'name': 'SweatChipChop Inc.',
            'attendance_overtime_validation': 'no_validation',
            'absence_management': True,
        })
        cls.company.resource_calendar_id.tz = 'Europe/Brussels'
        cls.ruleset = cls.env['hr.attendance.overtime.ruleset'].with_company(cls.company).create({
            'name': 'Ruleset schedule quantity',
            'rule_ids': [Command.create({
                    'name': 'Rule schedule quantity',
                    'base_off': 'quantity',
                    'expected_hours_from_contract': True,
                    'quantity_period': 'day',
                })],
        })

        cls.company_1 = cls.env['res.company'].create({
            'name': 'Overtime Inc.',
            'absence_management': True,
        })
        cls.company_1.resource_calendar_id.tz = 'Europe/Brussels'
        cls.ruleset_1 = cls.env['hr.attendance.overtime.ruleset'].with_company(cls.company_1).create({
            'name': 'Ruleset schedule quantity',
            'rule_ids': [Command.create({
                    'name': 'Rule schedule quantity',
                    'base_off': 'quantity',
                    'expected_hours_from_contract': True,
                    'quantity_period': 'day',
                })],
        })

        cls.user = new_test_user(cls.env, login='fru', groups='base.group_user,hr_attendance.group_hr_attendance_manager', company_id=cls.company.id).with_company(cls.company)
        cls.employee = cls.env['hr.employee'].create({
            'name': "Marie-Edouard De La Court",
            'user_id': cls.user.id,
            'company_id': cls.company.id,
            'tz': 'UTC',
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'ruleset_id': cls.ruleset.id,
        })
        cls.other_employee = cls.env['hr.employee'].create({
            'name': 'Yolanda',
            'company_id': cls.company.id,
            'tz': 'UTC',
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'ruleset_id': cls.ruleset.id,
        })
        cls.jpn_employee = cls.env['hr.employee'].create({
            'name': 'Sacha',
            'company_id': cls.company.id,
            'tz': 'Asia/Tokyo',
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'ruleset_id': cls.ruleset.id,
        })
        set_calendar_and_tz(cls.jpn_employee, 'Asia/Tokyo')

        cls.honolulu_employee = cls.env['hr.employee'].create({
            'name': 'Susan',
            'company_id': cls.company.id,
            'tz': 'Pacific/Honolulu',
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'ruleset_id': cls.ruleset.id,
        })
        set_calendar_and_tz(cls.honolulu_employee, 'Pacific/Honolulu')

        cls.europe_employee = cls.env['hr.employee'].with_company(cls.company_1).create({
            'name': 'Schmitt',
            'company_id': cls.company_1.id,
            'tz': 'Europe/Brussels',
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'resource_calendar_id': cls.company_1.resource_calendar_id.id,
            'ruleset_id': cls.ruleset_1.id,
        })
        set_calendar_and_tz(cls.europe_employee, 'Europe/Brussels')

        cls.no_contract_employee = cls.env['hr.employee'].create({
            'name': 'No Contract',
            'company_id': cls.company.id,
            'tz': 'UTC',
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'date_version': date(2020, 1, 1),
            'contract_date_start': False,
        })
        cls.future_contract_employee = cls.env['hr.employee'].create({
            'name': 'Future contract',
            'company_id': cls.company.id,
            'tz': 'UTC',
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2030, 1, 1),
        })

        cls.calendar_flex_40h = cls.env['resource.calendar'].create({
            'name': 'Flexible 40 hours/week',
            'company_id': cls.company.id,
            'hours_per_day': 8,
            'flexible_hours': True,
            'full_time_required_hours': 40,
        })

        cls.flexible_employee = cls.env['hr.employee'].create({
            'name': 'Flexi',
            'company_id': cls.company.id,
            'tz': 'UTC',
            'resource_calendar_id': cls.calendar_flex_40h.id,
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'ruleset_id': cls.ruleset.id,
        })

    def test_overtime_company_settings(self):
        self.company.write({
            "attendance_overtime_validation": "by_manager",
        })

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 8, 0),
            'check_out': datetime(2021, 1, 4, 20, 0),
        })

        self.assertEqual(attendance.overtime_status, 'to_approve')
        self.assertAlmostEqual(attendance.validated_overtime_hours, 0, 2)
        self.assertEqual(attendance.employee_id.total_overtime, 0)

        attendance.action_approve_overtime()

        self.assertEqual(attendance.overtime_status, 'approved')
        self.assertAlmostEqual(attendance.validated_overtime_hours, 3, 2)
        self.assertAlmostEqual(attendance.employee_id.total_overtime, 3, 2)

        attendance.action_refuse_overtime()
        self.assertEqual(attendance.employee_id.total_overtime, 0, 0)

    def test_simple_undertime(self):
        checkin_am = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 8, 0),
        })
        self.env['hr.attendance'].create({
            'employee_id': self.other_employee.id,
            'check_in': datetime(2021, 1, 4, 8, 0),
            'check_out': datetime(2021, 1, 4, 15, 0),
        })

        overtime = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id), ('date', '=', date(2021, 1, 4))])
        self.assertFalse(overtime, 'No overtime record should exist for that employee')

        checkin_am.write({'check_out': datetime(2021, 1, 4, 12, 0)})
        overtime = checkin_am._linked_overtimes()
        self.assertTrue(overtime, 'An overtime record should be created')
        self.assertEqual(overtime.duration, -4)

        checkin_pm = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 13, 0),
        })
        overtime = checkin_pm._linked_overtimes()
        self.assertFalse(overtime.exists(), 'Overtime duration should not exist when an attendance has not been checked out.')
        checkin_pm.write({'check_out': datetime(2021, 1, 4, 18, 0)})
        overtime = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id), ('date', '=', date(2021, 1, 4))])
        self.assertAlmostEqual(overtime.duration, 1)
        self.assertAlmostEqual(self.employee.total_overtime, 1)

    def test_simple_undertime_multiple_rules(self):
        """ Checks that only the least consequent undertime of the rules is considered."""
        ruleset = self.env['hr.attendance.overtime.ruleset'].with_company(self.company).create({
            'name': 'Ruleset schedule quantity',
            'rule_ids': [Command.create({
                    'name': 'Rule schedule quantity',
                    'base_off': 'quantity',
                    'expected_hours_from_contract': False,
                    'expected_hours': 8.0,
                    'quantity_period': 'day',
                }),
                Command.create({
                    'name': 'Rule schedule quantity',
                    'base_off': 'quantity',
                    'expected_hours_from_contract': False,
                    'expected_hours': 10.0,
                    'quantity_period': 'day',
                })],
        })
        self.employee.ruleset_id = ruleset

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 13, 0),
            'check_out': datetime(2021, 1, 4, 18, 0),
        })

        self.assertEqual(attendance.overtime_hours, -3.0)
        overtime = attendance._linked_overtimes()
        self.assertEqual(len(overtime), 1, 'Only one overtime record should be created')
        self.assertEqual(overtime.duration, -3.0)

    def test_simple_undertime_multiple_rules_on_several_periods(self):
        """Whatever the period type, only the least consequent undertime of the rules is considered.
        """
        ruleset = self.env['hr.attendance.overtime.ruleset'].with_company(self.company).create({
            'name': 'Ruleset schedule quantity',
            'rule_ids': [Command.create({
                    'name': 'Rule schedule quantity',
                    'base_off': 'quantity',
                    'expected_hours_from_contract': False,
                    'expected_hours': 8.0,
                    'quantity_period': 'day',
                }),
                Command.create({
                    'name': 'Rule schedule quantity',
                    'base_off': 'quantity',
                    'expected_hours_from_contract': False,
                    'expected_hours': 40.0,
                    'quantity_period': 'week',
                })],
        })
        self.employee.ruleset_id = ruleset

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 13, 0),
            'check_out': datetime(2021, 1, 4, 18, 0),
        })

        self.assertEqual(attendance.overtime_hours, -3.0)
        overtime = attendance._linked_overtimes()
        self.assertEqual(len(overtime), 1, 'Only one overtime record should be created')
        self.assertEqual(overtime.duration, -3.0)

    def test_undertime_change_employee(self):
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 7, 0),
            'check_out': datetime(2021, 1, 4, 15, 0),
        })

        self.assertEqual(self.employee.total_overtime, -1)
        self.assertEqual(self.other_employee.total_overtime, 0)

        self.other_employee.ruleset_id = self.ruleset
        self.env['hr.attendance'].create({
            'employee_id': self.other_employee.id,
            'check_in': datetime(2021, 1, 4, 7, 0),
            'check_out': datetime(2021, 1, 4, 15, 0),
        })
        attendance.unlink()
        self.assertEqual(self.other_employee.total_overtime, -1)
        self.assertEqual(self.employee.total_overtime, 0)

    def test_undertime_far_timezones(self):
        # Since dates have to be stored in utc these are the tokyo timezone times for 7-12 / 13-18 (UTC+9)
        (self.jpn_employee | self.honolulu_employee).ruleset_id = self.ruleset
        self.env['hr.attendance'].create({
            'employee_id': self.jpn_employee.id,
            'check_in': datetime(2021, 1, 4, 1, 0),
            'check_out': datetime(2021, 1, 4, 4, 0),
        })
        # Lunch time is at 3-4 UTC in Tokyo, and we don't work during lunch.

        # Same but for alaskan times (UTC-10)
        self.env['hr.attendance'].create({
            'employee_id': self.honolulu_employee.id,
            'check_in': datetime(2021, 1, 4, 17, 0),
            'check_out': datetime(2021, 1, 4, 20, 0),
        })
        self.assertAlmostEqual(self.jpn_employee.total_overtime, -6, 2)
        self.assertAlmostEqual(self.honolulu_employee.total_overtime, -5, 2)

    def test_undertime_lunch(self):
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 8, 0),
            'check_out': datetime(2021, 1, 4, 13, 0),
        })
        self.assertEqual(self.employee.total_overtime, -4, 'There should be only -4 since the employee did not work through the lunch period.')

    def test_undertime_hours_with_multiple_attendance(self):
        m_attendance_1 = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2023, 1, 3, 8, 0),
            'check_out': datetime(2023, 1, 3, 12, 0),
        })
        self.assertAlmostEqual(m_attendance_1.overtime_hours, -4, 2)

        m_attendance_2 = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2023, 1, 3, 13, 0),
            'check_out': datetime(2023, 1, 3, 17, 0),
        })
        self.assertAlmostEqual(m_attendance_1.overtime_hours, 0, 2)
        self.assertAlmostEqual(m_attendance_2.overtime_hours, 0, 2)

        m_attendance_3 = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2023, 1, 3, 18, 0),
            'check_out': datetime(2023, 1, 3, 19, 0),
        })
        self.assertAlmostEqual(m_attendance_1.overtime_hours, 0, 2)
        self.assertAlmostEqual(m_attendance_2.overtime_hours, 0, 2)
        self.assertAlmostEqual(m_attendance_3.overtime_hours, 1, 2)

        overtime_2 = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id),
                                                                ('date', '=', datetime(2023, 1, 3))])
        # Total overtime for that day : 5 hours
        self.assertEqual(len(overtime_2), 1, "Only one overtime record should be created for that day.")
        self.assertEqual(overtime_2.duration, 1)

        # Attendance Modification case

        m_attendance_3.write({
            'check_out': datetime(2023, 1, 3, 20, 00),
        })
        self.assertAlmostEqual(m_attendance_3.overtime_hours, 2, 2)

        # Deleting previous attendances should update correctly the overtime hours in other attendances
        m_attendance_2.unlink()
        self.assertAlmostEqual(m_attendance_3.overtime_hours, -2, 2)

    def test_undertime_across_days_timezones(self):
        self.europe_employee.ruleset_id = self.ruleset

        early_attendance = self.env['hr.attendance'].create({
            'employee_id': self.europe_employee.id,
            'check_in': datetime(2024, 5, 27, 23, 30),
            'check_out': datetime(2024, 5, 28, 4, 30),
        })
        self.assertAlmostEqual(early_attendance.overtime_hours, -3, 2)

        # Total overtime for that day : -3 hours
        overtime_record = early_attendance.linked_overtime_ids
        self.assertAlmostEqual(overtime_record.duration, -3, 2)

        # Check that the calendar's timezones take priority and that overtimes and attendances dates are consistent
        self.europe_employee.resource_calendar_id.tz = 'America/New_York'

        early_attendance2 = self.env['hr.attendance'].create({
            'employee_id': self.europe_employee.id,
            'check_in': datetime(2024, 5, 30, 3, 0),  # 23:00 NY prev day
            'check_out': datetime(2024, 5, 30, 10, 0),  # 6:00 NY
        })
        # First day you only work 1 hour and second day you work 6 hours, that's -1 hours of overtime
        self.assertAlmostEqual(early_attendance2.overtime_hours, -1, 2)

        overtime_record2 = early_attendance2.linked_overtime_ids
        self.assertEqual(len(overtime_record2), 1, "One undertime records should be created for that attendance.")
        self.assertAlmostEqual(overtime_record2.duration, -1, 2)

        early_attendance3 = self.env['hr.attendance'].create({
            'employee_id': self.europe_employee.id,
            'check_in': datetime(2024, 5, 31, 4, 0),  # 00:00 NY
            'check_out': datetime(2024, 5, 31, 10, 0),  # 6:00 NY
        })
        self.assertAlmostEqual(early_attendance3.overtime_hours, -2, 2)

    def test_undertime_hours_flexible_resource(self):
        """ Test the computation of overtime hours for a single flexible resource with 8 hours_per_day.
        =========
        Test Case
        1) | 8:00  | 16:00 | -> No overtime
        2) | 12:00 | 18:00 | -> -2 hours of overtime
        3) | 10:00 | 22:00 | -> 4 hours of overtime
        """
        self.flexible_employee.ruleset_id = self.ruleset
        # 1) 8:00 - 16:00 should contain 0 hours of overtime
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.flexible_employee.id,
            'check_in': datetime(2023, 1, 2, 8, 0),
            'check_out': datetime(2023, 1, 2, 16, 0),
        })
        self.assertEqual(attendance.overtime_hours, 0, 'There should be no overtime for the flexible resource.')

        # 2) 12:00 - 18:00 should contain -2 hours of overtime
        # as we expect the employee to work 8 hours per day
        attendance.write({
            'check_in': datetime(2023, 1, 3, 12, 0),
            'check_out': datetime(2023, 1, 3, 18, 0),
        })
        self.assertAlmostEqual(attendance.overtime_hours, -2, 2, 'There should be -2 hours of overtime for the flexible resource.')

        # 3) 10:00 - 22:00 should contain 4 hours of overtime
        attendance.write({
            'check_in': datetime(2023, 1, 4, 10, 0),
            'check_out': datetime(2023, 1, 4, 22, 0),
        })
        self.assertAlmostEqual(attendance.overtime_hours, 4, 2, 'There should be 4 hours of overtime for the flexible resource.')

    def test_undertime_hours_multiple_flexible_resources(self):
        """ Test the computation of overtime hours for multiple flexible resources on a single workday with 8 hours_per_day.
        =========

        We should see that the overtime hours are recomputed correctly when new attendance records are created.

        Test Case
        1) | 8:00  | 12:00 | -> -4 hours of overtime
        2) (| 8:00 | 12:00 |, | 13:00 | 15:00 |) -> (0, -2) hours of overtime
        3) (| 8:00 | 12:00 |, | 13:00 | 15:00 |, | 16:00 | 18:00 |) -> (0, 0, 0) hours of overtime
        """
        self.flexible_employee.ruleset_id = self.ruleset

        # 1) 8:00 - 12:00 should contain -4 hours of overtime
        attendance_1 = self.env['hr.attendance'].create({
            'employee_id': self.flexible_employee.id,
            'check_in': datetime(2023, 1, 2, 8, 0),
            'check_out': datetime(2023, 1, 2, 12, 0),
        })
        self.assertAlmostEqual(attendance_1.overtime_hours, -4, 2, 'There should be -4 hours of overtime for the flexible resource.')

        # 2) 8:00 - 12:00 and 13:00 - 15:00 should contain 0 and -2 hours of overtime
        attendance_2 = self.env['hr.attendance'].create({
            'employee_id': self.flexible_employee.id,
            'check_in': datetime(2023, 1, 2, 13, 0),
            'check_out': datetime(2023, 1, 2, 15, 0),
        })
        self.assertEqual(attendance_1.overtime_hours, 0, 'There should be no overtime for the flexible resource.')
        self.assertAlmostEqual(attendance_2.overtime_hours, -2, 2, 'There should be -2 hours of overtime for the flexible resource.')

        # 3) 8:00 - 12:00, 13:00 - 15:00 and 16:00 - 18:00 should contain 0, 0 and 0 hours of overtime
        attendance_3 = self.env['hr.attendance'].create({
            'employee_id': self.flexible_employee.id,
            'check_in': datetime(2023, 1, 2, 16, 0),
            'check_out': datetime(2023, 1, 2, 18, 0),
        })
        self.assertEqual(attendance_1.overtime_hours, 0, 'There should be no overtime for the flexible resource.')
        self.assertEqual(attendance_2.overtime_hours, 0, 'There should be no overtime for the flexible resource.')
        self.assertEqual(attendance_3.overtime_hours, 0, 'There should be no overtime for the flexible resource.')

    def test_refuse_overtime(self):
        self.company.write({
            "attendance_overtime_validation": "by_manager",
        })

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2023, 1, 2, 8, 0),
            'check_out': datetime(2023, 1, 2, 12, 0),
        })

        overtime = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id)])
        overtime.action_approve()

        self.assertEqual(attendance.validated_overtime_hours, -4)
        self.assertEqual(attendance.overtime_hours, attendance.validated_overtime_hours)

        attendance.action_refuse_overtime()
        self.assertEqual(attendance.validated_overtime_hours, 0)

    def test_no_validation_extra_hours_change(self):
        """
         In case of attendances requiring no validation, check that extra hours are not recomputed
         if the value is different from `validated_hours` (meaning it has been modified by the user).
        """
        self.company.attendance_overtime_validation = "no_validation"

        attendance = self.env['hr.attendance']
        # Form is used here as it will send a `validated_overtime_hours` value of 0 when saved.
        # This should not be considered as a manual edition of the field by the user.
        with Form(attendance) as attendance_form:
            attendance_form.employee_id = self.employee
            attendance_form.check_in = datetime(2023, 1, 2, 8, 0)
            attendance_form.check_out = datetime(2023, 1, 2, 15, 0)
        attendance = attendance_form.save()

        self.assertAlmostEqual(attendance.overtime_hours, -2, 2)
        self.assertAlmostEqual(attendance.validated_overtime_hours, -2, 2)

        attendance.linked_overtime_ids.manual_duration = previous = -1.5
        self.assertNotEqual(attendance.validated_overtime_hours, attendance.overtime_hours)

        # Create another attendance for the same employee
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2023, 1, 4, 8, 0),
            'check_out': datetime(2023, 1, 4, 18, 0),
        })
        self.assertEqual(attendance.validated_overtime_hours, previous, "Extra hours shouldn't be recomputed")

    def test_overtime_employee_tolerance(self):
        self.ruleset.rule_ids[0].employee_tolerance = 10 / 60
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

        overtime = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id)])
        self.assertFalse(overtime, 'No overtime should be counted because of the tolerance.')

        self.ruleset.rule_ids[0].employee_tolerance = 4 / 60
        self.ruleset.action_regenerate_overtimes()

        overtime = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id)])
        self.assertTrue(overtime, 'Overtime entry should exist since the tolerance has been lowered.')
        self.assertAlmostEqual(overtime.duration, -(10 / 60), places=2, msg='Overtime should be equal to -10 minutes.')

    def test_overtime_on_multiple_days(self):
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 8, 8, 0),  # Friday 8 AM - 17 PM work, 17 - 24 overtime (7 hours)
            'check_out': datetime(2021, 1, 9, 3, 0),  # Saturday 0-3 AM overtime (3 hours)
        })

        overtime = attendance._linked_overtimes()
        self.assertEqual(len(overtime), 2, 'There should be 2 overtime records for that attendance.')
        self.assertEqual(sum(overtime.mapped('duration')), 10, 'There should be a total of 10 hours of overtime for that attendance.')

        attendance.write({
            'check_out': datetime(2021, 1, 8, 20, 0),
        })

        overtime = attendance._linked_overtimes()
        self.assertEqual(len(overtime), 1, 'There should have only 1 overtime for that attendance after modification.')
        self.assertEqual(sum(overtime.mapped('duration')), 3, 'There should be a total of 3 hours of overtime for that attendance after modification.')

        all_overtimes = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id)])
        self.assertEqual(len(all_overtimes), 1, 'There should be only 1 overtime record in total for that employee.')
