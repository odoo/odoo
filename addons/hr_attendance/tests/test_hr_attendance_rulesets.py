# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime
from freezegun import freeze_time

from odoo import Command
from odoo.tests import new_test_user, Form
from odoo.tests.common import tagged, TransactionCase


@tagged('hr_attendance_overtime_ruleset')
class TestHrAttendanceOvertime(TransactionCase):
    """ Tests for overtime """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ruleset = cls.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Ruleset schedule quantity',
            'rule_ids': [
                Command.create({
                    'name': 'Rule schedule quantity',
                    'base_off': 'quantity',
                    'quantity_period': 'day',
                    'expected_hours': 8,
                    'paid': True,
                    'amount_rate': 150,
                }),
                Command.create({
                    'name': 'Rule schedule quantity',
                    'base_off': 'quantity',
                    'quantity_period': 'day',
                    'expected_hours': 10,
                    'paid': True,
                    'amount_rate': 200,
                }),
                Command.create({
                    'name': 'Rule schedule quantity',
                    'base_off': 'quantity',
                    'quantity_period': 'week',
                    'expected_hours': 40,
                    'paid': True,
                    'amount_rate': 150,
                }),
            ],
        })

        cls.company = cls.env['res.company'].create({
            'name': 'SweatChipChop Inc.',
            'attendance_overtime_validation': 'no_validation',
        })
        cls.company.resource_calendar_id = cls.env.company.resource_calendar_id = cls.env['resource.calendar'].create({
            'name': 'Standard 40 hours/week (No Lunch)',
            'company_id': cls.env.company.id,
            'hours_per_day': 7.6,
            'full_time_required_hours': 38,
            'attendance_ids': [
                (5, 0, 0),  # Clear existing attendances
                (0, 0, {'name': 'Monday', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 16, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 16, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 16, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 16, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 16, 'day_period': 'morning'}),
            ],
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
            'ruleset_id': cls.ruleset.id
        })

    def test_daily_overtime_8_hours_rule(self):
        with freeze_time("2021-01-04"):
            # Attendance: 10 hours (8 expected + 2 overtime at 150%)
            attendance = self.env['hr.attendance'].create({
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 1, 4, 8, 0),
                'check_out': datetime(2021, 1, 4, 18, 0)
            })

            self.assertAlmostEqual(attendance.employee_id.total_overtime, 2, 2, msg="2 hours overtime at 150% should yield 2 hours total overtime")

    def test_daily_overtime_10_hours_rule(self):
        """ Test daily overtime for the 10-hour rule """
        with freeze_time("2021-01-04"):
            # Attendance: 12 hours (10 expected + 2 overtime at 200%)
            attendance = self.env['hr.attendance'].create({
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 1, 4, 8, 0),
                'check_out': datetime(2021, 1, 4, 20, 0)
            })

            self.assertAlmostEqual(attendance.employee_id.total_overtime, 4.0, 2, msg="2 hours overtime at 200% should yield 4 hours total overtime")

    def test_no_overtime(self):
        """ Test no overtime when working expected hours or less """
        with freeze_time("2021-01-04"):
            # Attendance: 8 hours (exactly 8 expected, no overtime)
            attendance = self.env['hr.attendance'].create({
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 1, 4, 8, 0),
                'check_out': datetime(2021, 1, 4, 16, 0)
            })
            self.assertAlmostEqual(attendance.employee_id.total_overtime, 0.0, 2, msg="No overtime should be recorded for 8 hours or less")

    def test_weekly_overtime(self):
        """ Test weekly overtime for the 40-hour rule """
        with freeze_time("2021-01-04"):
            # Week: Mon-Fri, 10 hours/day = 50 hours total (40 expected + 10 overtime at 200%)
            [
                self.env['hr.attendance'].create({
                    'employee_id': self.employee.id,
                    'check_in': datetime(2021, 1, day, 8, 0),
                    'check_out': datetime(2021, 1, day, 18, 0)
                }) for day in range(4, 9)  # Monday to Friday
            ]
            # todo : Fixme weekly overtime is being double counted
            self.assertAlmostEqual(self.employee.total_overtime, 18, 2, msg="10 hours weekly overtime at 200% should yield 18 hours total overtime")

    def test_multiple_attendances_same_day(self):
        """ Test multiple attendances in one day """
        with freeze_time("2021-01-04"):
            # Two attendances: 6 hours + 6 hours = 12 hours (10 expected + 2 overtime at 200%)
            self.env['hr.attendance'].create([
                {
                    'employee_id': self.employee.id,
                    'check_in': datetime(2021, 1, 4, 8, 0),
                    'check_out': datetime(2021, 1, 4, 14, 0)
                },
                {
                    'employee_id': self.employee.id,
                    'check_in': datetime(2021, 1, 4, 14, 0),
                    'check_out': datetime(2021, 1, 4, 20, 0)
                }
            ])

            self.assertAlmostEqual(self.employee.total_overtime, 4.0, 2, msg="2 hours overtime at 200% should yield 4 hours total overtime")

    def test_partial_week(self):
        """ Test partial week with overtime """
        with freeze_time("2021-01-04"):
            # Week: Mon-Wed, 12 hours/day = 36 hours total (no weekly overtime, daily overtime applies)
            [
                self.env['hr.attendance'].create({
                    'employee_id': self.employee.id,
                    'check_in': datetime(2021, 1, day, 8, 0),
                    'check_out': datetime(2021, 1, day, 20, 0)
                }) for day in range(4, 7)  # Monday to Wednesday
            ]

            self.assertAlmostEqual(self.employee.total_overtime, 12.0, 2, msg="3 days of 2 hours overtime at 200% should yield 12 hours total overtime")

    def test_access_ruleset_on_employee(self):
        """
        Test the access rights of the ruleset on the employee
        Only the employee admin should be able to see and change the ruleset on the employee
        """
        user = new_test_user(self.env, login='usr', groups='hr.group_hr_user', company_id=self.company.id).with_company(self.company)
        employee = self.env['hr.employee'].with_company(self.company).create({'name': "Employee Test"})
        with Form(employee.with_user(user)) as employee_form:
            self.assertFalse("ruleset_id" in employee_form._view['fields'])

        # HR Mangers should be able to see the ruleset on the employee
        user.group_ids |= self.env.ref('hr.group_hr_manager')
        # fix le truc chelou de pas pouvoir ecrire la surrement les access rule
        with Form(employee.with_user(user)) as employee_form:
            self.assertTrue("ruleset_id" in employee_form._view['fields'])
            employee_form.record.ruleset_id = self.ruleset.id

    def test_is_manager_with_overtime(self):
        """ Test the computation of is_manager with overtime """
        user = new_test_user(self.env, login='usr', groups='hr_attendance.group_hr_attendance_officer', company_id=self.company.id).with_company(self.company)
        self.employee.attendance_manager_id = user.id
        attendance = self.env['hr.attendance'].with_company(self.company).create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 8, 0),
            'check_out': datetime(2021, 1, 4, 20, 0)
        })
        self.assertTrue(attendance.with_user(user).linked_overtime_ids.is_manager)
