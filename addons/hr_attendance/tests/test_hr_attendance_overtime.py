# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime
from freezegun import freeze_time

from odoo import Command
from odoo.tests import Form, new_test_user
from odoo.tests.common import tagged, TransactionCase


@tagged('hr_attendance_overtime')
class TestHrAttendanceOvertime(TransactionCase):
    """ Tests for overtime """

    @classmethod
    def setUpClass(cls):
        def set_calendar_and_tz(employee, tz):
            employee.resource_calendar_id = cls.env['resource.calendar'].create({
                'name': f'Default Calendar ({tz})',
                'tz': tz,
            })
        super().setUpClass()
        cls.ruleset = cls.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Ruleset schedule quantity',
            'rule_ids': [Command.create({
                    'name': 'Rule schedule quantity',
                    'base_off': 'quantity',
                    'expected_hours_from_contract': True,
                    'quantity_period': 'day',
                })],
        })

        cls.company = cls.env['res.company'].create({
            'name': 'SweatChipChop Inc.',
            'attendance_overtime_validation': 'no_validation',
            # 'overtime_company_threshold': 10,
            # 'overtime_employee_threshold': 10,
        })
        cls.company.resource_calendar_id.tz = 'Europe/Brussels'
        cls.company_1 = cls.env['res.company'].create({
            'name': 'Overtime Inc.',
        })
        cls.company_1.resource_calendar_id.tz = 'Europe/Brussels'
        cls.user = new_test_user(cls.env, login='fru', groups='base.group_user,hr_attendance.group_hr_attendance_manager', company_id=cls.company.id).with_company(cls.company)
        cls.employee = cls.env['hr.employee'].create({
            'name': "Marie-Edouard De La Court",
            'user_id': cls.user.id,
            'company_id': cls.company.id,
            'tz': 'UTC',
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'ruleset_id': cls.ruleset.id
        })
        cls.other_employee = cls.env['hr.employee'].create({
            'name': 'Yolanda',
            'company_id': cls.company.id,
            'tz': 'UTC',
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'ruleset_id': cls.ruleset.id
        })
        cls.jpn_employee = cls.env['hr.employee'].create({
            'name': 'Sacha',
            'company_id': cls.company.id,
            'tz': 'Asia/Tokyo',
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'ruleset_id': cls.ruleset.id
        })
        set_calendar_and_tz(cls.jpn_employee, 'Asia/Tokyo')

        cls.honolulu_employee = cls.env['hr.employee'].create({
            'name': 'Susan',
            'company_id': cls.company.id,
            'tz': 'Pacific/Honolulu',
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'ruleset_id': cls.ruleset.id
        })
        set_calendar_and_tz(cls.honolulu_employee, 'Pacific/Honolulu')

        cls.europe_employee = cls.env['hr.employee'].with_company(cls.company_1).create({
            'name': 'Schmitt',
            'company_id': cls.company_1.id,
            'tz': 'Europe/Brussels',
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'resource_calendar_id': cls.company_1.resource_calendar_id.id,
            'ruleset_id': cls.ruleset.id
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
            'ruleset_id': cls.ruleset.id
        })

    def test_overtime_company_settings(self):
        self.company.write({
            "attendance_overtime_validation": "by_manager"
        })

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 8, 0),
            'check_out': datetime(2021, 1, 4, 20, 0)
        })

        self.assertEqual(attendance.overtime_status, 'to_approve')
        # self.assertAlmostEqual(attendance.validated_overtime_hours, 3, 2) -- TODO naja: seems wrong: why did we want that?
        self.assertAlmostEqual(attendance.validated_overtime_hours, 0, 2)
        self.assertEqual(attendance.employee_id.total_overtime, 0)

        attendance.action_approve_overtime()

        self.assertEqual(attendance.overtime_status, 'approved')
        self.assertAlmostEqual(attendance.validated_overtime_hours, 3, 2)
        self.assertAlmostEqual(attendance.employee_id.total_overtime, 3, 2)

        attendance.action_refuse_overtime()
        self.assertEqual(attendance.employee_id.total_overtime, 0, 0)

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

        overtime = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id), ('date', '=', date(2021, 1, 4))])
        self.assertFalse(overtime, 'No overtime record should exist for that employee')

        checkin_am.write({'check_out': datetime(2021, 1, 4, 12, 0)})
        # TODO naja: should work after negative works
        # overtime = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id), ('date', '=', date(2021, 1, 4))])
        # self.assertTrue(overtime, 'An overtime record should be created')
        # self.assertEqual(overtime.duration, -4)

        checkin_pm = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 13, 0)
        })
        self.assertEqual(overtime.duration, 0, 'Overtime duration should be 0 when an attendance has not been checked out.')
        checkin_pm.write({'check_out': datetime(2021, 1, 4, 18, 0)})
        # self.assertTrue(overtime.exists(), 'Overtime should not be deleted')
        overtime = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id), ('date', '=', date(2021, 1, 4))])
        self.assertAlmostEqual(overtime.duration, 1)
        self.assertAlmostEqual(self.employee.total_overtime, 1)

    def test_overtime_weekend(self):
        self.env['hr.attendance.overtime.rule'].create({
            'name': "Rule non working days",
            'base_off': 'timing',
            'timing_type': 'non_work_days',
            'ruleset_id': self.ruleset.id,
        })

        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 2, 8, 0),
            'check_out': datetime(2021, 1, 2, 11, 0)
        })

        overtime = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id), ('date', '=', date(2021, 1, 2))])
        self.assertTrue(overtime, 'Overtime should be created')
        self.assertEqual(overtime.duration, 3, 'Should have 3 hours of overtime')
        self.assertEqual(self.employee.total_overtime, 3, 'Should still have 3 hours of overtime')

    def test_overtime_multiple(self):
        self.env['hr.attendance.overtime.rule'].create({
            'name': "Rule non working days",
            'base_off': 'timing',
            'timing_type': 'non_work_days',
            'ruleset_id': self.ruleset.id,
        })
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 2, 8, 0),
            'check_out': datetime(2021, 1, 2, 19, 0)
        })
        self.assertEqual(self.employee.total_overtime, 11)
        # self.assertEqual(self.employee.total_overtime, 3)

        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 7, 0),
            'check_out': datetime(2021, 1, 4, 17, 0)
        })
        self.assertEqual(self.employee.total_overtime, 12)

        attendance.unlink()
        self.assertAlmostEqual(self.employee.total_overtime, 1, 2)

    def test_overtime_change_employee(self):
        Attendance = self.env['hr.attendance']
        attendance = Attendance.create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 7, 0),
            'check_out': datetime(2021, 1, 4, 18, 0)
        })

        self.assertEqual(self.employee.total_overtime, 2)
        self.assertEqual(self.other_employee.total_overtime, 0)

        self.other_employee.ruleset_id = self.ruleset
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
        (self.jpn_employee | self.honolulu_employee).ruleset_id = self.ruleset
        self.env['hr.attendance'].create({
            'employee_id': self.jpn_employee.id,
            'check_in': datetime(2021, 1, 4, 1, 0),
            'check_out': datetime(2021, 1, 4, 12, 0),
        })

        # Same but for alaskan times (UTC-10)
        self.env['hr.attendance'].create({
            'employee_id': self.honolulu_employee.id,
            'check_in': datetime(2021, 1, 4, 17, 0),
            'check_out': datetime(2021, 1, 5, 4, 0),
        })
        self.assertAlmostEqual(self.jpn_employee.total_overtime, 2, 2)
        # todo attendance_rulesets : fixme timezone issues
        self.assertAlmostEqual(self.honolulu_employee.total_overtime, 5, 2)

    def test_overtime_unclosed(self):
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 8, 0),
        })
        overtime = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id)])
        self.assertFalse(overtime, 'Overtime entry should not exist at this point.')
        # Employees goes to eat
        attendance.write({
            'check_out': datetime(2021, 1, 4, 20, 0),
        })
        overtime = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id)])
        self.assertTrue(overtime, 'An overtime entry should have been created.')
        self.assertEqual(overtime.duration, 3, 'User should have 3 hours of overtime.')

    def test_overtime_company_threshold(self):
        self.ruleset.rule_ids[0].employer_tolerance = 10 / 60  # 10 minutes
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
        overtime = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id)])
        self.assertFalse(overtime, 'No overtime should be counted because of the threshold.')

        self.ruleset.rule_ids[0].employer_tolerance = 4 / 60  # 10 minutes
        self.ruleset.action_regenerate_overtimes()

        overtime = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id)])
        self.assertTrue(overtime, 'Overtime entry should exist since the threshold has been lowered.')
        self.assertAlmostEqual(overtime.duration, 10 / 60, msg='Overtime should be equal to 10 minutes.')

    # TODO naja: make rework after negative overtimes
    # def test_overtime_employee_threshold(self):
    #     self.env['hr.attendance'].create([
    #         {
    #             'employee_id': self.employee.id,
    #             'check_in': datetime(2021, 1, 4, 8, 5),
    #             'check_out': datetime(2021, 1, 4, 12, 0),
    #         },
    #         {
    #             'employee_id': self.employee.id,
    #             'check_in': datetime(2021, 1, 4, 13, 0),
    #             'check_out': datetime(2021, 1, 4, 16, 55),
    #         }
    #     ])

    #     overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id)])
    #     self.assertFalse(overtime, 'No overtime should be counted because of the threshold.')

    #     self.company.write({
    #         'overtime_employee_threshold': 4,
    #     })

    #     overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id)])
    #     self.assertTrue(overtime, 'Overtime entry should exist since the threshold has been lowered.')
    #     self.assertAlmostEqual(overtime.duration, -(10 / 60), msg='Overtime should be equal to -10 minutes.')
    #
    # def test_overtime_both_threshold(self):
    #     self.env['hr.attendance'].create([
    #         {
    #             'employee_id': self.employee.id,
    #             'check_in': datetime(2021, 1, 4, 8, 5),
    #             'check_out': datetime(2021, 1, 4, 12, 0),
    #         },
    #         {
    #             'employee_id': self.employee.id,
    #             'check_in': datetime(2021, 1, 4, 13, 0),
    #             'check_out': datetime(2021, 1, 4, 17, 5),
    #         }
    #     ])
    #     overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id)])
    #     self.assertFalse(overtime, 'No overtime should be counted because of the threshold.')

    #     self.company.write({
    #         'overtime_employee_threshold': 4,
    #     })

    #     overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id)])
    #     self.assertTrue(overtime, 'Overtime entry should exist since the employee threshold has been lowered.')
    #     self.assertAlmostEqual(overtime.duration, -(5 / 60), msg='Overtime should be equal to -5 minutes.')

    #     self.company.write({
    #         'overtime_company_threshold': 4,
    #     })

    #     overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id)])
    #     self.assertFalse(overtime, 'Overtime entry should be unlinked since both overtime cancel each other.')

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
        overtime_1 = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id),
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

        overtime_2 = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id),
                                                                ('date', '=', datetime(2023, 1, 3))])
        # Total overtime for that day : 5 hours
        self.assertEqual(sum(overtime_2.mapped('duration')), 5)

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

        self.europe_employee.ruleset_id = self.ruleset
        # Create an attendance record for early check-in
        early_attendance = self.env['hr.attendance'].create({
            'employee_id': self.europe_employee.id,
            'check_in': datetime(2024, 5, 27, 23, 30),
            'check_out': datetime(2024, 5, 28, 13, 30)
        })

        # 5:00 -> 19:00[in emp tz] should contain 5 hours of overtime
        self.assertAlmostEqual(early_attendance.overtime_hours, 5)

        # Total overtime for that day : 5 hours
        overtime_record = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.europe_employee.id),
                                                              ('date', '=', datetime(2024, 5, 28))])
        self.assertAlmostEqual(overtime_record.duration, 5)

        # Check that the calendar's timezones take priority and that overtimes and attendances dates are consistent
        self.europe_employee.resource_calendar_id.tz = 'America/New_York'

        early_attendance2 = self.env['hr.attendance'].create({
            'employee_id': self.europe_employee.id,
            'check_in': datetime(2024, 5, 30, 3, 0),  # 23:00 NY prev day -- attendance should be for the 29th
            'check_out': datetime(2024, 5, 30, 16, 0)  # 12:00 NY
        })

        # expected = 5 (13 - 8 work - 1 for europe lunch) -- since attendance is for the next day the lunch isn't accounted for
        # TODO naja: should we refactor the weird way we handle lunch in general ?
        self.assertAlmostEqual(early_attendance2.overtime_hours, 4)

        # Total overtime for the 29th (not the 30th): 5 hours
        overtime_record2 = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.europe_employee.id),
                                                              ('date', '=', datetime(2024, 5, 29))])
        self.assertAlmostEqual(overtime_record2.duration, 4)

    @freeze_time("2024-02-01 23:00:00")
    def test_auto_check_out(self):
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 1
        })
        self.env['hr.attendance'].create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 2, 1, 8, 0),
            'check_out': datetime(2024, 2, 1, 11, 0)
        },
        {
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 2, 1, 11, 0),
            'check_out': datetime(2024, 2, 1, 13, 0)
        }
        ])

        attendance_utc_pending = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 2, 1, 14, 0)
        })

        # Based on the employee's working calendar, they should be within the allotted hours.
        attendance_utc_pending_within_allotted_hours = self.env['hr.attendance'].create({
            'employee_id': self.europe_employee.id,
            'check_in': datetime(2024, 2, 1, 20, 0, 0)
        })

        attendance_utc_done = self.env['hr.attendance'].create({
            'employee_id': self.other_employee.id,
            'check_in': datetime(2024, 2, 1, 8, 0),
            'check_out': datetime(2024, 2, 1, 17, 0)
        })

        attendance_jpn_pending = self.env['hr.attendance'].create({
            'employee_id': self.jpn_employee.id,
            'check_in': datetime(2024, 2, 1, 12, 0)
        })

        attendance_flexible_pending = self.env['hr.attendance'].create({
            'employee_id': self.flexible_employee.id,
            'check_in': datetime(2024, 2, 1, 12, 0)
        })

        self.assertEqual(attendance_utc_pending.check_out, False)
        self.assertEqual(attendance_utc_pending_within_allotted_hours.check_out, False)
        self.assertEqual(attendance_utc_done.check_out, datetime(2024, 2, 1, 17, 0))
        self.assertEqual(attendance_jpn_pending.check_out, False)
        self.assertEqual(attendance_flexible_pending.check_out, False)

        self.env['hr.attendance']._cron_auto_check_out()

        self.assertEqual(attendance_utc_pending.check_out, datetime(2024, 2, 1, 19, 0))
        self.assertEqual(attendance_utc_pending_within_allotted_hours.check_out, False)
        self.assertEqual(attendance_utc_done.check_out, datetime(2024, 2, 1, 17, 0))
        self.assertEqual(attendance_jpn_pending.check_out, datetime(2024, 2, 1, 21, 0))

        # Employee with flexible working schedule should not be checked out
        self.assertEqual(attendance_flexible_pending.check_out, False)

    @freeze_time("2024-02-1 23:00:00")
    def test_auto_check_out_more_one_day_delta(self):
        """ Test that the checkout is correct if the delta between the check in and now is > 24 hours"""
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 1
        })

        attendance_utc_pending = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, 30, 8, 0)
        })

        self.assertEqual(attendance_utc_pending.check_out, False)
        self.env['hr.attendance']._cron_auto_check_out()
        self.assertEqual(attendance_utc_pending.check_out, datetime(2024, 1, 30, 18, 0))

    @freeze_time("2024-02-05 23:00:00")
    def test_auto_checkout_past_day(self):
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 1,
        })
        attendance_utc_pending_7th_day = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 2, 1, 14, 0),
        })
        self.assertEqual(attendance_utc_pending_7th_day.check_out, False)
        self.env['hr.attendance']._cron_auto_check_out()
        self.assertEqual(attendance_utc_pending_7th_day.check_out, datetime(2024, 2, 1, 23, 0))

    @freeze_time("2024-02-2 20:00:00")
    def test_auto_check_out_calendar_tz(self):
        """Check expected working hours and previously worked hours are from the correct day when
        using a calendar with a different timezone."""
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 1
        })
        self.jpn_employee.resource_calendar_id.tz = 'Asia/Tokyo'  # UTC+9
        self.jpn_employee.resource_calendar_id.attendance_ids.filtered(lambda a: a.dayofweek == "4" and a.day_period in ["lunch", "afternoon"]).unlink()

        attendances_jpn = self.env['hr.attendance'].create([
            {
                'employee_id': self.jpn_employee.id,
                'check_in': datetime(2024, 2, 1, 6, 0),
                'check_out': datetime(2024, 2, 1, 7, 0)
            },
            {
                'employee_id': self.jpn_employee.id,
                'check_in': datetime(2024, 2, 1, 21, 0),
                'check_out': datetime(2024, 2, 1, 22, 0)
            },
            {
                'employee_id': self.jpn_employee.id,
                'check_in': datetime(2024, 2, 1, 23, 0)
            }
        ])

        self.env['hr.attendance']._cron_auto_check_out()
        self.assertEqual(attendances_jpn[2].check_out, datetime(2024, 2, 2, 3, 0), "Check-out after 4 hours (4 hours expected from calendar + 1 hours tolerance - 1 hour previous attendance)")

    def test_auto_check_out_lunch_period(self):
        Attendance = self.env['hr.attendance']
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 1
        })
        morning, afternoon = Attendance.create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, 1, 8, 0),
            'check_out': datetime(2024, 1, 1, 12, 0)
        },
        {
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, 1, 13, 0)
        }])

        with freeze_time("2024-01-01 22:00:00"):
            Attendance._cron_auto_check_out()
            self.assertEqual(morning.worked_hours + afternoon.worked_hours, 9)  # 8 hours from calendar's attendances + 1 hour of tolerance
            self.assertEqual(afternoon.check_out, datetime(2024, 1, 1, 18, 0))

    def test_auto_check_out_two_weeks_calendar(self):
        """Test case: two weeks calendar with different attendances depending on the week. No morning attendance on
        wednesday of the first week."""
        Attendance = self.env['hr.attendance']
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 0
        })
        self.employee.resource_calendar_id.switch_calendar_type()
        self.employee.resource_calendar_id.attendance_ids.search([("dayofweek", "=", "2"), ("week_type", '=', '0'), ("day_period", "in", ["morning", "lunch"])]).unlink()

        with freeze_time("2025-03-05 22:00:00"):
            att = Attendance.create({
                'employee_id': self.employee.id,
                'check_in': datetime(2025, 3, 5, 8, 0)
            })
            Attendance._cron_auto_check_out()
            self.assertEqual(att.worked_hours, 4)
            self.assertEqual(att.check_out, datetime(2025, 3, 5, 12, 0))

        with freeze_time("2025-03-12 22:00:00"):
            att = Attendance.create({
                'employee_id': self.employee.id,
                'check_in': datetime(2025, 3, 12, 8, 0),
            })
            Attendance._cron_auto_check_out()
            self.assertEqual(att.worked_hours, 8)
            self.assertEqual(att.check_out, datetime(2025, 3, 12, 17, 0))

    # @freeze_time("2024-02-01 14:00:00")
    # def test_absence_management(self):
    # TODO no more absence management
    #     self.company.write({
    #         'absence_management': True,
    #     })

    #     self.env['hr.attendance'].create({
    #         'employee_id': self.employee.id,
    #         'check_in': datetime(2024, 1, 31, 8, 0),
    #         'check_out': datetime(2024, 1, 31, 17, 0)
    #     })

    #     self.env['hr.attendance'].create({
    #         'employee_id': self.employee.id,
    #         'check_in': datetime(2024, 2, 1, 8, 0),
    #         'check_out': datetime(2024, 2, 1, 17, 0)
    #     })

    #     self.env['hr.attendance'].create({
    #         'employee_id': self.other_employee.id,
    #         'check_in': datetime(2024, 2, 1, 8, 0),
    #         'check_out': datetime(2024, 2, 1, 17, 0)
    #     })

    #     self.env['hr.attendance'].create({
    #         'employee_id': self.jpn_employee.id,
    #         'check_in': datetime(2024, 2, 1, 1, 0),
    #         'check_out': datetime(2024, 2, 1, 10, 0)

    #     })

    #     self.env['hr.attendance'].create({
    #         'employee_id': self.honolulu_employee.id,
    #         'check_in': datetime(2024, 2, 1, 17, 0),
    #         'check_out': datetime(2024, 2, 2, 2, 0)
    #     })

    #     self.env['hr.attendance'].create({
    #         'employee_id': self.europe_employee.id,
    #         'check_in': datetime(2024, 2, 1, 8, 0),
    #         'check_out': datetime(2024, 2, 1, 17, 0)
    #     })

    #     self.env['hr.attendance'].create({
    #         'employee_id': self.flexible_employee.id,
    #         'check_in': datetime(2024, 2, 1, 8, 0),
    #         'check_out': datetime(2024, 2, 1, 16, 0)
    #     })

    #     self.assertAlmostEqual(self.employee.total_overtime, 0, 2)
    #     self.assertAlmostEqual(self.other_employee.total_overtime, 0, 2)
    #     self.assertAlmostEqual(self.jpn_employee.total_overtime, 0, 2)
    #     self.assertAlmostEqual(self.honolulu_employee.total_overtime, 0, 2)
    #     self.assertAlmostEqual(self.europe_employee.total_overtime, 0, 2)
    #     self.assertAlmostEqual(self.flexible_employee.total_overtime, 0, 2)

    #     self.env['hr.attendance']._cron_absence_detection()

    #     # Check that absences were correctly attributed
    #     self.assertAlmostEqual(self.other_employee.total_overtime, -8, 2)
    #     self.assertAlmostEqual(self.jpn_employee.total_overtime, -8, 2)
    #     self.assertAlmostEqual(self.honolulu_employee.total_overtime, -8, 2)

    #     # Employee Checked in yesterday, no absence found
    #     self.assertAlmostEqual(self.employee.total_overtime, 0, 2)

    #     # Flexible schedule employee, no absence found
    #     self.assertAlmostEqual(self.flexible_employee.total_overtime, 0, 2)

    #     # Other company with setting disabled
    #     self.assertAlmostEqual(self.europe_employee.total_overtime, 0, 2)

    #     # Employee with no contract or future contract
    #     # self.assertAlmostEqual(self.no_contract_employee.total_overtime, 0, 2)
    #     # self.assertAlmostEqual(self.future_contract_employee.total_overtime, 0, 2)

    def test_overtime_hours_flexible_resource(self):
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
            'check_out': datetime(2023, 1, 2, 16, 0)
        })
        self.assertEqual(attendance.overtime_hours, 0, 'There should be no overtime for the flexible resource.')

        # 2) 12:00 - 18:00 should contain -2 hours of overtime
        # as we expect the employee to work 8 hours per day
        attendance.write({
            'check_in': datetime(2023, 1, 3, 12, 0),
            'check_out': datetime(2023, 1, 3, 18, 0)
        })
        # TODO naja: logic should rework after negative logic
        # self.assertAlmostEqual(attendance.overtime_hours, -2, 2, 'There should be -2 hours of overtime for the flexible resource.')
        # for no negative overtime -> 0
        self.assertAlmostEqual(attendance.overtime_hours, 0, 2, 'There should be -2 hours of overtime for the flexible resource.')

        # 3) 10:00 - 22:00 should contain 4 hours of overtime
        attendance.write({
            'check_in': datetime(2023, 1, 4, 10, 0),
            'check_out': datetime(2023, 1, 4, 22, 0)
        })
        self.assertAlmostEqual(attendance.overtime_hours, 4, 2, 'There should be 4 hours of overtime for the flexible resource.')

    def test_overtime_hours_multiple_flexible_resources(self):
        """ Test the computation of overtime hours for multiple flexible resources on a single workday with 8 hours_per_day.
        =========

        We should see that the overtime hours are recomputed correctly when new attendance records are created.

        Test Case
        1) | 8:00  | 12:00 | -> -4 hours of overtime
        2) (| 8:00 | 12:00 |, | 13:00 | 15:00 |) -> (0, -2) hours of overtime
        3) (| 8:00 | 12:00 |, | 13:00 | 15:00 |, | 16:00 | 18:00 |) -> (0, 0, 0) hours of overtime
        """
        self.flexible_employee.ruleset_id = self.ruleset

        # TODO naja: logic should rework after negative logic
        # self.assertAlmostEqual(attendance.overtime_hours, -2, 2, 'There should be -2 hours of overtime for the flexible resource.')
        # for no negative overtime -> 0

        # 1) 8:00 - 12:00 should contain -4 hours of overtime
        attendance_1 = self.env['hr.attendance'].create({
            'employee_id': self.flexible_employee.id,
            'check_in': datetime(2023, 1, 2, 8, 0),
            'check_out': datetime(2023, 1, 2, 12, 0)
        })
        self.assertAlmostEqual(attendance_1.overtime_hours, 0, 2, 'There should be -4 hours of overtime for the flexible resource.')

        # 2) 8:00 - 12:00 and 13:00 - 15:00 should contain 0 and -2 hours of overtime
        attendance_2 = self.env['hr.attendance'].create({
            'employee_id': self.flexible_employee.id,
            'check_in': datetime(2023, 1, 2, 13, 0),
            'check_out': datetime(2023, 1, 2, 15, 0)
        })
        self.assertEqual(attendance_1.overtime_hours, 0, 'There should be no overtime for the flexible resource.')
        # self.assertAlmostEqual(attendance_2.overtime_hours, -2, 2, 'There should be -2 hours of overtime for the flexible resource.')
        self.assertAlmostEqual(attendance_2.overtime_hours, 0, 2, 'There should be 0 hours of overtime for the flexible resource.')

        # 3) 8:00 - 12:00, 13:00 - 15:00 and 16:00 - 18:00 should contain 0, 0 and 0 hours of overtime
        attendance_3 = self.env['hr.attendance'].create({
            'employee_id': self.flexible_employee.id,
            'check_in': datetime(2023, 1, 2, 16, 0),
            'check_out': datetime(2023, 1, 2, 18, 0),
        })
        self.assertEqual(attendance_1.overtime_hours, 0, 'There should be no overtime for the flexible resource.')
        self.assertEqual(attendance_2.overtime_hours, 0, 'There should be no overtime for the flexible resource.')
        self.assertEqual(attendance_3.overtime_hours, 0, 'There should be no overtime for the flexible resource.')

    def test_overtime_hours_fully_flexible_resource(self):
        """ Test the computation of overtime hours for a fully flexible resource.
        Fully flexible resources should not have any overtime. """

        # take the flexible resource and set the resource calendar to a fully flexible one
        self.flexible_employee.resource_calendar_id = False

        # 1) 8:00 - 16:00 should contain 0 hours of overtime
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.flexible_employee.id,
            'check_in': datetime(2023, 1, 2, 8, 0),
            'check_out': datetime(2023, 1, 2, 16, 0)
        })
        self.assertEqual(attendance.overtime_hours, 0, 'There should be no overtime for the fully flexible resource.')

        # 2) 16:00 - 09:00 (next day) should contain 0 hours of overtime
        attendance.write({
            'check_in': datetime(2023, 1, 3, 16, 0),
            'check_out': datetime(2023, 1, 4, 9, 0)
        })
        self.assertEqual(attendance.overtime_hours, 0, 'There should be no overtime for the fully flexible resource.')

    def test_refuse_timeoff(self):
        self.company.write({
            "attendance_overtime_validation": "by_manager"
        })

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2023, 1, 2, 8, 0),
            'check_out': datetime(2023, 1, 3, 12, 0)
        })

        overtime = self.env['hr.attendance.overtime.line'].search([
            ('employee_id', '=', self.employee.id),
        ])
        overtime.action_approve()

        self.assertEqual(attendance.validated_overtime_hours, 19)
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
            attendance_form.check_out = datetime(2023, 1, 2, 18, 0)
        attendance = attendance_form.save()

        self.assertAlmostEqual(attendance.overtime_hours, 1, 2)
        self.assertAlmostEqual(attendance.validated_overtime_hours, 1, 2)

        attendance._linked_overtimes().manual_duration = previous = 0.5
        self.assertNotEqual(attendance.validated_overtime_hours, attendance.overtime_hours)

        # Create another attendance for the same employee
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2023, 1, 4, 8, 0),
            'check_out': datetime(2023, 1, 4, 18, 0)
        })
        self.assertEqual(attendance.validated_overtime_hours, previous, "Extra hours shouldn't be recomputed")

    def _check_overtimes(self, overtimes, vals_list):
        self.assertEqual(len(overtimes), len(vals_list), "Wrong number of overtimes")
        for overtime, vals in zip(overtimes, vals_list):
            for k, v in vals.items():
                self.assertEqual(overtime[k], v)

    def test_overtime_rule_timing(self):
        version = self.employee._get_version(date(2025, 8, 20))
        ruleset = self.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Test Timing Ruleset',
            'rule_ids': [
                Command.create({
                    'name': "Company Schedule",
                    'base_off': 'timing',
                    'timing_type': 'schedule',
                    'resource_calendar_id': self.company.resource_calendar_id.id,
                }),
                Command.create({
                    'name': "Naptime",
                    'base_off': 'timing',
                    'timing_type': 'work_days',
                    'timing_start': 14,
                    'timing_stop': 15,
                }),
            ],
        })

        version.ruleset_id = ruleset

        # attendance 7 -> 16 (5-14) on a wednesday. Expected overtimes:
        # * Naptime 14-15 (= 12-13 utc)
        # * Company Schedule: 7-8 (= 5-6 utc)
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 8, 20, 5, 0),  # a wednesday, 7 am utc
            'check_out': datetime(2025, 8, 20, 14, 0),
        })

        overtimes = self.env['hr.attendance.overtime.line'].search([
            ('employee_id', '=', self.employee.id),
        ])
        self._check_overtimes(overtimes, [
            {  # 7:00 -> 8:00
                'date': date(2025, 8, 20),
                'time_start': datetime(2025, 8, 20, 5, 0),
                'time_stop': datetime(2025, 8, 20, 6, 0),
            },
            {  # 14:00 -> 15:00
                'date': date(2025, 8, 20),
                'time_start': datetime(2025, 8, 20, 12, 0),
                'time_stop': datetime(2025, 8, 20, 13, 0),
            },
        ])

    def test_overtime_rule_quantity(self):
        version = self.employee._get_version(date(2025, 8, 20))
        ruleset = self.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Test Qty Ruleset',
            'rule_ids': [
                Command.create({
                    'name': "> 9h/d",
                    'base_off': 'quantity',
                    'quantity_period': 'day',
                    'expected_hours_from_contract': False,
                    'expected_hours': 9,
                }),
                Command.create({
                    'name': "Weekly Overtime",
                    'base_off': 'quantity',
                    'quantity_period': 'week',
                    'expected_hours_from_contract': False,
                    'expected_hours': 40,
                }),
            ],
        })

        version.ruleset_id = ruleset

        # 10h on monday: 1h daily ot
        # 8h on tue-thu (24h)
        # 10h on friday: 1h daily ot
        # 10 + 24 + 10 - 40 = 4 weekly ot
        # Expected result:
        # * monday, friday: 1 h daily ot each on the end of the day, that are also weekly
        # * friday: 4h weekly, 1 overlaps with the hours
        # * total = 1 + 4 = 5
        self.env['hr.attendance'].create([
            # monday 8-19 (10h bc 1 hours lunch)
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2025, 8, 18, 6, 0),
                'check_out': datetime(2025, 8, 18, 17, 0),
            },
            # friday 8-19: 10h
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2025, 8, 22, 6, 0),
                'check_out': datetime(2025, 8, 22, 17, 0),
            },
            # tue-thu 8-17: 8h each
            *[{
                'employee_id': self.employee.id,
                'check_in': datetime(2025, 8, day, 6, 0),
                'check_out': datetime(2025, 8, day, 15, 0),
            } for day in range(19, 22)]
        ])

        overtimes = self.env['hr.attendance.overtime.line'].search([
            ('employee_id', '=', self.employee.id),
        ])

        self.assertAlmostEqual(sum(ot.duration for ot in overtimes), 5.0, 2)
        self._check_overtimes(overtimes, [
            {  # monday 18:00->19:00 (weekly + monday daily)
                'date': date(2025, 8, 18),
                'time_start': datetime(2025, 8, 18, 16, 0),
                'time_stop': datetime(2025, 8, 18, 17, 0),
            },
            {  # friday 15:00->18:00 (weekly)
                'date': date(2025, 8, 22),
                'time_start': datetime(2025, 8, 22, 13, 0),
                'time_stop': datetime(2025, 8, 22, 16, 0),
            },
            {  # friday 18:00->19:00 (weekly + friday daily)
                'date': date(2025, 8, 22),
                'time_start': datetime(2025, 8, 22, 16, 0),
                'time_stop': datetime(2025, 8, 22, 17, 0),
            },
        ])

    def test_overtime_rule_combined(self):
        # TODO
        pass
