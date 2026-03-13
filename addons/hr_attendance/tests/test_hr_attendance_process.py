# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
import pytz
from datetime import datetime, date
from unittest.mock import patch

from odoo import fields, Command
from odoo.tests import new_test_user
from odoo.tests.common import tagged, TransactionCase, freeze_time
from odoo.tools import float_compare


def _get_attendance_hour_start_and_end(target_date, hour) -> tuple[datetime, datetime]:
    hour_start = datetime(target_date.year, target_date.month, target_date.day, hour)
    # "seconds=-1" insted of "microseconds=-1" because attendance check_in/check_out aren't that precise
    hour_end = hour_start + relativedelta(hours=1, seconds=-1)
    return hour_start, hour_end


@tagged('attendance_process')
class TestHrAttendance(TransactionCase):
    """Test for presence validity"""

    @classmethod
    def setUpClass(cls):
        super(TestHrAttendance, cls).setUpClass()
        cls.user = new_test_user(cls.env, login='fru', groups='base.group_user')
        cls.user_no_pin = new_test_user(cls.env, login='gru', groups='base.group_user')
        cls.test_employee = cls.env['hr.employee'].create({
            'name': "François Russie",
            'user_id': cls.user.id,
            'pin': '1234',
        })
        cls.employee_kiosk = cls.env['hr.employee'].create({
            'name': "Machiavel",
            'pin': '5678',
        })

        one_week_calendar_attendances = []
        # Add attendances from Monday to Friday
        for i in range(5):
            one_week_calendar_attendances.extend(cls._get_day_attendances(week_day=i))
        cls.one_week_calendar = cls.env['resource.calendar'].create({
            'name': 'One week Calendar',
            'attendance_ids': one_week_calendar_attendances,
            'tz': 'UTC',
        })
        cls.one_week_employee = cls.env['hr.employee'].create({
            'name': "One week employee",
            'pin': '1111',
            'resource_calendar_id': cls.one_week_calendar.id,
        })

        two_weeks_calendar_attendances = []
        for i in range(5):
            # First week, add attendances from Monday to Friday
            two_weeks_calendar_attendances.extend(cls._get_day_attendances(week_day=i, week_type='0'))
        for i in range(2, 7):
            # Second week, add attendances from Wednesday to Sunday
            two_weeks_calendar_attendances.extend(cls._get_day_attendances(week_day=i, week_type='1'))
        cls.two_weeks_calendar = cls.env['resource.calendar'].create({
            'name': 'Two weeks Calendar',
            'attendance_ids': two_weeks_calendar_attendances,
            'two_weeks_calendar': True,
            'tz': 'UTC',
        })
        cls.two_weeks_employee = cls.env['hr.employee'].create({
            'name': "Two weeks employee",
            'pin': '2222',
            'resource_calendar_id': cls.two_weeks_calendar.id,
        })

    @classmethod
    def _get_day_attendances(cls, week_day, week_type=False):
        """ 8 hours of work separated by 1 hour of lunch """
        return (
            Command.create({'name': f'Day {week_day} Morning', 'dayofweek': str(week_day), 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'week_type': week_type}),
            Command.create({'name': f'Day {week_day} Lunch', 'dayofweek': str(week_day), 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch', 'week_type': week_type}),
            Command.create({'name': f'Day {week_day} Afternoon', 'dayofweek': str(week_day), 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon', 'week_type': week_type}),
        )

    def setUp(self):
        super().setUp()
        # Cache error if not done during setup
        (self.test_employee | self.employee_kiosk).last_attendance_id.unlink()

    def test_employee_state(self):
        # Make sure the attendance of the employee will display correctly
        assert self.test_employee.attendance_state == 'checked_out'
        self.test_employee._attendance_action_change()
        assert self.test_employee.attendance_state == 'checked_in'
        self.test_employee._attendance_action_change()
        assert self.test_employee.attendance_state == 'checked_out'

    def test_employee_group_id(self):
        # Create attendance for one of them
        self.env['hr.attendance'].create({
            'employee_id': self.employee_kiosk.id,
            'check_in': '2025-08-01 08:00:00',
            'check_out': '2025-08-01 17:00:00',
        })
        context = self.env.context.copy()
        # Specific to gantt view.
        context['gantt_start_date'] = fields.Datetime.now()
        context['allowed_company_ids'] = [self.env.company.id]

        groups = self.env['hr.attendance'].read_group(
            domain=[],
            fields=['employee_id'],
            groupby=['employee_id']
        )

        grouped_employee_ids = [g['employee_id'][0] for g in groups]

        # Check that only the employee with attendance appears
        self.assertNotIn(self.test_employee.id, grouped_employee_ids)
        self.assertIn(self.employee_kiosk.id, grouped_employee_ids)

        # Check that no group has a count of 0
        for group in groups:
            self.assertGreater(group['employee_id_count'], 0)

        groups = self.env['hr.attendance'].with_context(**context).read_group(
            domain=[],
            fields=['employee_id'],
            groupby=['employee_id']
        )

        grouped_employee_ids = [g['employee_id'][0] for g in groups]

        # Check that both employees appears
        self.assertIn(self.test_employee.id, grouped_employee_ids)
        self.assertIn(self.employee_kiosk.id, grouped_employee_ids)

    def test_hours_today(self):
        """ Test day start is correctly computed according to the employee's timezone """

        def tz_datetime(year, month, day, hour, minute):
            tz = pytz.timezone('Europe/Brussels')
            return tz.localize(datetime(year, month, day, hour, minute)).astimezone(pytz.utc).replace(tzinfo=None)

        employee = self.env['hr.employee'].create({'name': 'Cunégonde', 'tz': 'Europe/Brussels'})
        self.env['hr.attendance'].create({
            'employee_id': employee.id,
            'check_in': tz_datetime(2019, 3, 1, 22, 0),  # should count from midnight in the employee's timezone (=the previous day in utc!)
            'check_out': tz_datetime(2019, 3, 2, 2, 0),
        })
        self.env['hr.attendance'].create({
            'employee_id': employee.id,
            'check_in': tz_datetime(2019, 3, 2, 11, 0),
        })

        # now = 2019/3/2 14:00 in the employee's timezone
        with patch.object(fields.Datetime, 'now', lambda: tz_datetime(2019, 3, 2, 14, 0).astimezone(pytz.utc).replace(tzinfo=None)):
            self.assertEqual(employee.hours_today, 5, "It should have counted 5 hours")

    @freeze_time("2024-02-1")
    def test_change_in_out_mode_when_manual_modification(self):
        company = self.env['res.company'].create({
            'name': 'Monsters, Inc.',
            'absence_management': True,
        })

        employee = self.env['hr.employee'].create({
            'name': "James P. Sullivan",
            'company_id': company.id,
        })

        self.env['hr.attendance']._cron_absence_detection()

        attendance = self.env['hr.attendance'].search([('employee_id', '=', employee.id)])

        self.assertEqual(attendance.in_mode, 'technical')
        self.assertEqual(attendance.out_mode, 'technical')
        self.assertEqual(attendance.color, 1)

        attendance.write({
            'check_in': datetime(2021, 1, 4, 8, 0),
            'check_out': datetime(2021, 1, 4, 17, 0),
        })

        self.assertEqual(attendance.in_mode, 'manual')
        self.assertEqual(attendance.out_mode, 'manual')
        self.assertEqual(attendance.color, 0)

    def test_expected_hours_one_week(self):
        """ For an employee who's supposed to be working from Monday to Friday,
            assert the `expected_hours` of his attendances are computed correctly
        """
        week_expected_hours = (8.0, 8.0, 8.0, 8.0, 8.0, 0, 0)
        # Starting with 2025-11-03 which is a Monday
        attendance_date = date(2025, 11, 3)
        for week_day in range(7):
            attendance = self.env['hr.attendance'].create({
                'check_in': datetime(attendance_date.year, attendance_date.month, attendance_date.day, 8, 0, 0),
                'check_out': datetime(attendance_date.year, attendance_date.month, attendance_date.day, 17, 0, 0),
                'employee_id': self.one_week_employee.id,
            })
            self.assertTrue(float_compare(attendance.expected_hours, week_expected_hours[week_day], precision_digits=2) == 0,
                f"For iteration {week_day} - date {attendance_date}, `expected_hours` is not computed correctly. Expected {week_expected_hours[week_day]}, got {attendance.expected_hours}")
            attendance_date += relativedelta(days=1)

    def test_expected_hours_one_week_multiple_attendances(self):
        """ For an employee who's supposed to be working from Monday to Friday,
            assert the `expected_hours` of his attendances are computed correctly
            when there are multiple attendances on the same day
        """
        week_expected_hours = (8.0, 8.0, 8.0, 8.0, 8.0, 0, 0)
        # Number of 1 hour attendance per day
        week_attendance_nbr = (1, 2, 3, 4, 5, 0, 0)
        # Starting with 2025-11-03 which is a Monday
        attendance_date = date(2025, 11, 3)
        for week_day in range(7):
            day_attendances = []
            # Add week_attendance_nbr[week_day] attendances of 1 hour
            for hour in range(8, week_attendance_nbr[week_day] + 8):
                hour_start, hour_end = _get_attendance_hour_start_and_end(attendance_date, hour)
                day_attendances.append(self.env['hr.attendance'].create({
                    'check_in': hour_start,
                    'check_out': hour_end,
                    'employee_id': self.one_week_employee.id,
                }))
            if not week_attendance_nbr[week_day]:
                continue
            # Division by `week_attendance_nbr[week_day]` : shitty stable fix for the pivot view so that it displays the "correct"
            # number of expected hour even when there are multiple attendances on the same day
            expected_expected_hour = week_expected_hours[week_day] / week_attendance_nbr[week_day]
            for attendance in day_attendances:
                self.assertTrue(float_compare(attendance.expected_hours, expected_expected_hour, precision_digits=4) == 0,
                    f"For iteration {week_day} - date: {attendance_date}, `expected_hours` is not computed correctly. "
                    f"Expected {expected_expected_hour}, got {attendance.expected_hours}")
            attendance_date += relativedelta(days=1)

    def test_expected_hours_one_week_multiple_attendances_with_leave(self):
        """ For an employee who's supposed to be working from Monday to Friday,
            assert the `expected_hours` of his attendances are computed correctly
            when there are multiple attendances on the same day.

            The employee takes a leave from Monday to Tuesday 12:00 (so expected_hour)
            of Monday is 0 and 4 for Tuesday (since employee is supposed to be working from 8 to 12).
            Also takes 2 hour on Wednesday (from 8:00 to 10:00), so 6 expected hours for this day.
        """
        self.env['resource.calendar.leaves'].create([{
                'resource_id': self.one_week_employee.resource_id.id,
                'date_from': datetime(2025, 11, 3, 8, 0, 0),
                'date_to': datetime(2025, 11, 4, 12, 0, 0),
            }, {
                'resource_id': self.one_week_employee.resource_id.id,
                'date_from': datetime(2025, 11, 5, 8, 0, 0),
                'date_to': datetime(2025, 11, 5, 10, 0, 0),
            }
        ])

        week_expected_hours = (0, 4.0, 6.0, 8.0, 8.0, 0, 0)
        # Number of 1 hour attendance per day
        week_attendance_nbr = (1, 2, 3, 4, 5, 0, 0)
        # Starting with 2025-11-03 which is a Monday
        attendance_date = date(2025, 11, 3)
        for week_day in range(7):
            day_attendances = []
            # Add week_attendance_nbr[week_day] attendances of 1 hour
            for hour in range(8, week_attendance_nbr[week_day] + 8):
                hour_start, hour_end = _get_attendance_hour_start_and_end(attendance_date, hour)
                day_attendances.append(self.env['hr.attendance'].create({
                    'check_in': hour_start,
                    'check_out': hour_end,
                    'employee_id': self.one_week_employee.id,
                }))
            if not week_attendance_nbr[week_day]:
                continue
            # Division by `week_attendance_nbr[week_day]` : shitty stable fix for the pivot view so that it displays the "correct"
            # number of expected hour even when there are multiple attendances on the same day
            expected_expected_hour = week_expected_hours[week_day] / week_attendance_nbr[week_day]
            for attendance in day_attendances:
                self.assertTrue(float_compare(attendance.expected_hours, expected_expected_hour, precision_digits=4) == 0,
                    f"For iteration {week_day} - date: {attendance_date}, `expected_hours` is not computed correctly. "
                    f"Expected {expected_expected_hour}, got {attendance.expected_hours}")
            attendance_date += relativedelta(days=1)

    def test_expected_hours_two_weeks(self):
        """ For an employee who's supposed to be working from Monday to Friday on week A and from Wednesday to Sunday on week B,
            assert the `expected_hours` of his attendances are computed correctly
        """
        week_0_expected_hours = (8.0, 8.0, 8.0, 8.0, 8.0, 0, 0)
        week_1_expected_hours = (0, 0, 8.0, 8.0, 8.0, 8.0, 8.0)
        # Starting with 2025-11-03 which is a Monday
        attendance_date = date(2025, 11, 3)
        for week in range(2):
            week_type = self.env['resource.calendar.attendance'].get_week_type(attendance_date)
            if week_type == 0:
                week_expected_hours = week_0_expected_hours
            else:
                week_expected_hours = week_1_expected_hours
            for week_day in range(7):
                attendance = self.env['hr.attendance'].create({
                    'check_in': datetime(attendance_date.year, attendance_date.month, attendance_date.day, 8, 0, 0),
                    'check_out': datetime(attendance_date.year, attendance_date.month, attendance_date.day, 17, 0, 0),
                    'employee_id': self.two_weeks_employee.id,
                })
                self.assertTrue(float_compare(attendance.expected_hours, week_expected_hours[week_day], precision_digits=2) == 0,
                    f"For {attendance_date}, at day loop iteration {week_day} of week loop iteration {week} (week_type {week_type}), "
                    f"`expected_hours` should be {week_expected_hours[week_day]} but is {attendance.expected_hours}")
                attendance_date += relativedelta(days=1)

    def test_expected_hours_two_week_multiple_attendances(self):
        """ For an employee who's supposed to be working from Monday to Friday on week A and from Wednesday to Sunday on week B,
            assert the `expected_hours` of his attendances are computed correctly when there are multiple attendances on the same day
        """
        week_0_expected_hours = (8.0, 8.0, 8.0, 8.0, 8.0, 0, 0)
        week_1_expected_hours = (0, 0, 8.0, 8.0, 8.0, 8.0, 8.0)
        # Number of 1 hour attendance per day
        week_attendance_nbr = (1, 2, 3, 4, 5, 6, 7)
        # Starting with 2025-11-03 which is a Monday
        attendance_date = date(2025, 11, 3)
        for week in range(2):
            week_type = self.env['resource.calendar.attendance'].get_week_type(attendance_date)
            if week_type == 0:
                week_expected_hours = week_0_expected_hours
            else:
                week_expected_hours = week_1_expected_hours
            for week_day in range(7):
                day_attendances = []
                # Add week_attendance_nbr[week_day] attendances of 1 hour
                for hour in range(8, week_attendance_nbr[week_day] + 8):
                    hour_start, hour_end = _get_attendance_hour_start_and_end(attendance_date, hour)
                    day_attendances.append(self.env['hr.attendance'].create({
                        'check_in': hour_start,
                        'check_out': hour_end,
                        'employee_id': self.two_weeks_employee.id,
                    }))
                if not week_attendance_nbr[week_day]:
                    continue
                # Division by `week_attendance_nbr[week_day]` : shitty stable fix for the pivot view so that it displays the "correct"
                # number of expected hour even when there are multiple attendances on the same day
                expected_expected_hour = week_expected_hours[week_day] / week_attendance_nbr[week_day]
                for attendance in day_attendances:
                    self.assertTrue(float_compare(attendance.expected_hours, expected_expected_hour, precision_digits=4) == 0,
                        f"For {attendance_date}, at day loop iteration {week_day} of week loop iteration {week} (week_type {week_type}), "
                        f"`expected_hours` should be {expected_expected_hour} but is {attendance.expected_hours}.")
                attendance_date += relativedelta(days=1)

    def test_expected_hours_two_week_multiple_attendances_with_leave(self):
        """ For an employee who's supposed to be working from Monday to Friday on week A and from Wednesday to Sunday on week B,
            assert the `expected_hours` of his attendances are computed correctly when there are multiple attendances on the same day.

            The employee takes a leave from Monday to Tuesday 12:00 (so expected_hour) of Monday is 0 and 4 for Tuesday of the week A
            (since employee is supposed to be working from 8 to 12).
            Also takes 2 hour on Wednesday of week 2 (from 8:00 to 10:00), so 6 expected hours for this day.
        """
        self.env['resource.calendar.leaves'].create([{
                # Week type 1 (week B)
                'resource_id': self.two_weeks_employee.resource_id.id,
                'date_from': datetime(2025, 11, 5, 8, 0, 0),
                'date_to': datetime(2025, 11, 5, 10, 0, 0),
            }, {
                # Week type 0 (week A)
                'resource_id': self.two_weeks_employee.resource_id.id,
                'date_from': datetime(2025, 11, 10, 8, 0, 0),
                'date_to': datetime(2025, 11, 11, 12, 0, 0),
            }
        ])
        # Starting with 2025-11-03 which is a Monday
        attendance_date = date(2025, 11, 3)

        # If `get_week_type` changes, then this test will break, those two lines assert that the error doesn't come from a change in the `get_week_type`
        self.assertEqual(self.env['resource.calendar.attendance'].get_week_type(attendance_date), 1)
        self.assertEqual(self.env['resource.calendar.attendance'].get_week_type(attendance_date + relativedelta(weeks=1)), 0)

        # Monday off and Tuesday off until 12:00
        week_0_expected_hours = (0, 4.0, 8.0, 8.0, 8.0, 0, 0)
        # Wednesday off 8:00 -> 10:00 so we get 6 expected hours instead of 8
        week_1_expected_hours = (0, 0, 6.0, 8.0, 8.0, 8.0, 8.0)
        # Number of 1 hour attendance per day
        week_attendance_nbr = (1, 2, 3, 4, 5, 6, 7)
        for week in range(2):
            week_type = self.env['resource.calendar.attendance'].get_week_type(attendance_date)
            if week_type == 0:
                week_expected_hours = week_0_expected_hours
            else:
                week_expected_hours = week_1_expected_hours
            for week_day in range(7):
                day_attendances = []
                # Add week_attendance_nbr[week_day] attendances of 1 hour
                for hour in range(8, week_attendance_nbr[week_day] + 8):
                    hour_start, hour_end = _get_attendance_hour_start_and_end(attendance_date, hour)
                    day_attendances.append(self.env['hr.attendance'].create({
                        'check_in': hour_start,
                        'check_out': hour_end,
                        'employee_id': self.two_weeks_employee.id,
                    }))
                if not week_attendance_nbr[week_day]:
                    continue
                # Division by `week_attendance_nbr[week_day]` : shitty stable fix for the pivot view so that it displays the "correct"
                # number of expected hour even when there are multiple attendances on the same day
                expected_expected_hour = week_expected_hours[week_day] / week_attendance_nbr[week_day]
                for attendance in day_attendances:
                    self.assertTrue(float_compare(attendance.expected_hours, expected_expected_hour, precision_digits=4) == 0,
                        f"For {attendance_date}, at day loop iteration {week_day} of week loop iteration {week} (week_type {week_type}), "
                        f"`expected_hours` should be {expected_expected_hour} but is {attendance.expected_hours}.")
                attendance_date += relativedelta(days=1)
