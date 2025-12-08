# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime

from odoo import Command
from odoo.tests import HttpCase, new_test_user
from odoo.tests.common import tagged


@tagged('hr_attendance_overtime')
class TestHrAttendanceOvertime(HttpCase):
    """ Tests for Undertime and Overtime """

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
        })
        cls.company.absence_management = True
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

    def test_daily_undertime_applies(self):
        """Daily undertime should generate negative overtime."""
        self.env.company.absence_management = True
        version = self.employee._get_version(date(2025, 8, 20))
        ruleset = self.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Daily Undertime',
            'rule_ids': [
                Command.create({
                    'name': '8h/day',
                    'base_off': 'quantity',
                    'quantity_period': 'day',
                    'expected_hours': 8,
                    'expected_hours_from_contract': False,
                    'compensable_as_leave': True,
                }),
            ],
        })

        version.ruleset_id = ruleset

        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 8, 20, 8, 0),
            'check_out': datetime(2025, 8, 20, 15, 0),
        })

        overtimes = self.env['hr.attendance.overtime.line'].search([
            ('employee_id', '=', self.employee.id),
        ])

        self.assertEqual(len(overtimes), 1)
        self.assertAlmostEqual(overtimes.duration, -2.0, 2, "There should be 2 hours of undertime.")

    def test_daily_undertime_consumes_overtime(self):
        """When a daily quantity rule creates both positive and negative overtime across days,
        negative (undertime) hours must reduce the employee's total overtime balance."""
        self.env.company.absence_management = True
        version = self.employee._get_version(date(2025, 8, 20))
        ruleset = self.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Daily 8h with compensable undertime',
            'rule_ids': [Command.create({
                'name': '8h/day',
                'base_off': 'quantity',
                'quantity_period': 'day',
                'expected_hours': 8,
                'expected_hours_from_contract': False,
                'compensable_as_leave': True,
            })],
        })
        version.ruleset_id = ruleset

        # Day 1: long attendance -> +4h overtime
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 8, 20, 8, 0),
            'check_out': datetime(2025, 8, 20, 21, 0),
        })
        # Day 2: short attendance -> -2h undertime (should deduct from total overtime)
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 8, 21, 8, 0),
            'check_out': datetime(2025, 8, 21, 15, 0),
        })

        # Fetch overtime records for both days
        overtimes = self.env['hr.attendance.overtime.line'].search([
            ('employee_id', '=', self.employee.id),
            ('date', 'in', [date(2025, 8, 20), date(2025, 8, 21)]),
        ])
        self.assertEqual(len(overtimes), 2)
        durations_by_date = {ot.date: ot.duration for ot in overtimes}
        self.assertAlmostEqual(durations_by_date.get(date(2025, 8, 20)), 4.0, 2)
        self.assertAlmostEqual(durations_by_date.get(date(2025, 8, 21)), -2.0, 2)

        # Total overtime must be reduced accordingly (4 - 2 = 2)
        self.assertAlmostEqual(self.employee.total_overtime, 2.0, 2)

    def test_undertime_applies_only_for_day_selector(self):
        """Ensure undertime is generated for quantity/day rules but not for quantity/week rules."""
        # Day-based quantity rule -> undertime should be created for a short single-day attendance
        self.env.company.absence_management = True
        version = self.employee._get_version(date(2025, 8, 20))
        ruleset_day = self.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Daily 8h',
            'rule_ids': [Command.create({
                'name': '8h/day',
                'base_off': 'quantity',
                'quantity_period': 'day',
                'expected_hours': 8,
                'expected_hours_from_contract': False,
                'compensable_as_leave': True,  # <--- must be true to generate undertime for day
            })],
        })
        version.ruleset_id = ruleset_day

        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 8, 20, 9, 0),
            'check_out': datetime(2025, 8, 20, 17, 0),  # 7h -> -1h undertime
        })
        overtimes_day = self.env['hr.attendance.overtime.line'].search([
            ('employee_id', '=', self.employee.id),
            ('date', '=', date(2025, 8, 20)),
        ])
        self.assertTrue(overtimes_day)
        self.assertAlmostEqual(sum(ot.duration for ot in overtimes_day), -1.0, 2)

        ruleset_week = self.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Weekly 40h',
            'rule_ids': [Command.create({
                'name': '40h/week',
                'base_off': 'quantity',
                'quantity_period': 'week',
                'expected_hours': 40,
                'expected_hours_from_contract': False,
                'compensable_as_leave': True,  # weekly compensable flag present but should be ignored for single day
            })],
        })
        version.ruleset_id = ruleset_week

        # Same single short attendance on another date -> no undertime because weekly selector is used
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 8, 27, 9, 0),
            'check_out': datetime(2025, 8, 27, 15, 0),  # 7h, but week-based rule must not create daily undertime
        })
        overtimes_week = self.env['hr.attendance.overtime.line'].search([
            ('employee_id', '=', self.employee.id),
            ('date', '=', date(2025, 8, 27)),
        ])
        # No undertime should be created for the single day with a week selector
        self.assertFalse(overtimes_week)

    def test_undertime_larger_than_overtime_results_negative_balance(self):
        """If undertime is larger than prior overtime, the net overtime becomes negative."""
        self.env.company.absence_management = True
        version = self.employee._get_version(date(2025, 8, 20))
        ruleset = self.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Daily 8h - compensable',
            'rule_ids': [Command.create({
                'name': '8h/day',
                'base_off': 'quantity',
                'quantity_period': 'day',
                'expected_hours': 8,
                'expected_hours_from_contract': False,
                'compensable_as_leave': True,
            })],
        })
        version.ruleset_id = ruleset

        # Day 1: +4h overtime (12h worked)
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 8, 20, 8, 0),
            'check_out': datetime(2025, 8, 20, 18, 0),
        })
        # Day 2: -5h undertime (3h worked) -> larger than +4h
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 8, 21, 8, 0),
            'check_out': datetime(2025, 8, 21, 15, 0),
        })

        overtimes = self.env['hr.attendance.overtime.line'].search([
            ('employee_id', '=', self.employee.id),
            ('date', 'in', [date(2025, 8, 20), date(2025, 8, 21)]),
        ])
        durations = {ot.date: ot.duration for ot in overtimes}
        self.assertAlmostEqual(durations.get(date(2025, 8, 20)), 1.0, 2)
        self.assertAlmostEqual(durations.get(date(2025, 8, 21)), -2.0, 2)
        # Net total should be -1.0 hours
        self.assertAlmostEqual(sum(durations.values()), -1.0, 2)

    def test_no_undertime_applies_without_absence_management(self):
        self.env.company.absence_management = False
        ruleset = self.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Daily 8h - compensable',
            'rule_ids': [Command.create({
                'name': '8h/day',
                'base_off': 'quantity',
                'quantity_period': 'day',
                'expected_hours': 8,
                'expected_hours_from_contract': False,
                'compensable_as_leave': True,
            })],
        })
        version = self.employee._get_version(date(2025, 8, 20))
        version.ruleset_id = ruleset

        # 5h undertime (3h worked) - No undertime must be applied
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 8, 20, 8, 0),
            'check_out': datetime(2025, 8, 20, 11, 0),
        })

        overtimes = self.env['hr.attendance.overtime.line'].search([
            ('employee_id', '=', self.employee.id),
            ('date', '=', date(2025, 8, 20)),
        ])
        self.assertAlmostEqual(overtimes.duration, 0, 2, "There should be 0 hours of undertime because absence management is not activated.")

        # 1h overtime (9h worked) - Overtime must still be applied
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 8, 21, 8, 0),
            'check_out': datetime(2025, 8, 21, 18, 0),
        })

        overtimes = self.env['hr.attendance.overtime.line'].search([
            ('employee_id', '=', self.employee.id),
            ('date', '=', date(2025, 8, 21)),
        ])
        self.assertAlmostEqual(overtimes.duration, 1, 2, "There should be 1 hour of overtime even though absence management is not activated.")
