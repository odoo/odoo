# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from freezegun import freeze_time

from odoo.exceptions import AccessError, ValidationError

from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestHrWorkEntryType(TestHrHolidaysCommon):

    def test_count_as(self):
        employee = self.env['hr.employee'].create({'name': 'Test Employee'})

        work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Paid Time Off',
            'code': 'Paid Time Off',
            'count_as': 'absence',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        with self.assertRaises(ValidationError):
            work_entry_type.allow_request_on_top = True

        worked_work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Worked Time',
            'code': 'Worked Time',
            'count_as': 'working_time',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        with self.assertRaises(ValidationError):
            worked_work_entry_type.elligible_for_accrual_rate = False

        leave_0 = self.env['hr.leave'].create({
            'name': 'Remote Work',
            'employee_id': employee.id,
            'work_entry_type_id': worked_work_entry_type.id,
            'request_date_from': '2025-09-01',  # Monday
            'request_date_to': '2025-09-05',
        })
        self.assertEqual(
            self.env['resource.calendar.leaves'].search([('holiday_id', '=', leave_0.id)]).count_as,
            'working_time',
        )
        with freeze_time('2025-09-03 13:00:00'):
            employee._compute_leave_status()
            self.assertFalse(employee.is_absent)
            self.assertEqual(employee.leave_date_from, leave_0.request_date_from)
            self.assertEqual(employee.leave_date_to, employee._get_first_working_interval_batch({employee.id: leave_0.date_to}).get(employee.id).date())

        # leaves overlap between time on and time off is allowed even without allow_request_on_top
        leave_1 = self.env['hr.leave'].create({
                'name': 'Doctor Appointment',
                'employee_id': employee.id,
                'work_entry_type_id': work_entry_type.id,
                'request_date_from': '2025-09-03',
                'request_date_to': '2025-09-03',
        })
        with self.assertRaises(ValidationError):
            self.env['hr.leave'].create({
                'name': 'Doctor Appointment',
                'employee_id': employee.id,
                'work_entry_type_id': work_entry_type.id,
                'request_date_from': '2025-09-03',
                'request_date_to': '2025-09-03',
            })

        self.assertEqual(
            self.env['resource.calendar.leaves'].search([('holiday_id', '=', leave_1.id)]).count_as,
            'absence'
        )
        with freeze_time('2025-09-03 13:00:00'):
            employee._compute_leave_status()
            self.assertTrue(employee.is_absent)

        with freeze_time('2025-09-04 13:00:00'):
            employee._compute_leave_status()
            self.assertFalse(employee.is_absent)

    def test_type_creation_right(self):
        # HrUser creates some holiday statuses -> crash because only HrManagers should do this
        with self.assertRaises(AccessError):
            self.env['hr.work.entry.type'].with_user(self.user_hruser_id).create({
                'name': 'UserCheats',
                'requires_allocation': False,
                'request_unit': 'day',
                'unit_of_measure': 'day',
            })

    def test_users_tz_shift_back(self):
        """This test follows closely related bug report and simulates its situation.
        We're located in Saipan (GMT+10) and we allocate some employee a leave from 19Aug-20Aug.
        Then we simulate opening the employee's calendar and attempting to allocate 21August.
        We should not get any valid allocation there as is it outsite of valid alocation period.

        2024-08-19      2024-08-20        2024-08-21
        ────┬─────────────────┬─────────────────┬─────►
            └─────────────────┘             requested
          Valid allocation period              day
        """
        employee = self.env['hr.employee'].create({'name': 'Test Employee'})
        work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Test Leave',
            'code': 'Test Leave',
            'request_unit': 'day',
            'unit_of_measure': 'day',
            })

        self.env['hr.leave.allocation'].sudo().create({
            'state': 'confirm',
            'work_entry_type_id': work_entry_type.id,
            'employee_id': employee.id,
            'date_from': '2024-08-19',
            'date_to': '2024-08-20',
        }).action_approve()

        work_entry_types = self.env['hr.work.entry.type'].with_context(
            default_date_from='2024-08-20 21:00:00',
            default_date_to='2024-08-21 09:00:00',
            tz='Pacific/Saipan',
            employee_id=employee.id,
            ).search([('has_valid_allocation', '=', True)], limit=1)

        self.assertFalse(work_entry_types, "Got valid leaves outside vaild period")

    def test_calendar_duration_excluding_public_holidays(self):
        """Test calendar duration calculation excluding public holidays"""

        calendar_work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Test Time Off (Exclude PH)',
            'code': 'Test Time Off 1',
            'requires_allocation': False,
            'count_days_as': 'calendar',
            'include_public_holidays_in_duration': False,
        })

        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2024, 6, 3, 0, 0, 0),
            'date_to': datetime(2024, 6, 3, 23, 59, 59),
            'calendar_id': False,
            'company_id': self.env.company.id,
        })

        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_hruser_id,
            'work_entry_type_id': calendar_work_entry_type.id,
            'request_date_from': date(2024, 6, 1),
            'request_date_to': date(2024, 6, 7),
        })

        days, hours = leave._get_durations()[leave.id]
        self.assertEqual(days, 6, "Duration should exclude 1 public holiday, resulting in 6 days")
        self.assertEqual(hours, 48, "Duration should be 6 * 8 hours when excluding public holidays")

    def test_calendar_duration_including_public_holidays(self):
        """Test calendar duration calculation including public holidays"""

        calendar_work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Test Time Off (Include PH)',
            'code': 'Test Time Off 2',
            'requires_allocation': False,
            'count_days_as': 'calendar',
            'include_public_holidays_in_duration': True,
        })

        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2024, 6, 3, 0, 0, 0),
            'date_to': datetime(2024, 6, 3, 23, 59, 59),
            'calendar_id': False,
            'company_id': self.env.company.id,
        })

        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_hruser_id,
            'work_entry_type_id': calendar_work_entry_type.id,
            'request_date_from': date(2024, 6, 1),
            'request_date_to': date(2024, 6, 7),
        })

        days, hours = leave._get_durations()[leave.id]
        self.assertEqual(days, 7, "Duration should include all 7 days even with public holiday")
        self.assertEqual(hours, 56, "Duration should be 7 * 8 hours when including public holidays")

    def test_calendar_duration_without_employee(self):
        """Duration of a 'calendar days' leave that has no employee yet

        This is the state of the form view when it is opened: no employee is set
        yet, so the leave is not part of the batched per-employee mappings and the
        calendar branch used to raise a KeyError. It has to fall back on the
        company calendar computation instead.
        """
        calendar_work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Test Time Off (No Employee)',
            'code': 'Test Time Off 5',
            'requires_allocation': False,
            'count_days_as': 'calendar',
            'request_unit': 'hour',
        })
        working_work_entry_type = calendar_work_entry_type.copy({
            'name': 'Test Time Off (No Employee, Working)',
            'code': 'Test Time Off 6',
            'count_days_as': 'working',
        })

        values = {
            'request_date_from': date(2024, 6, 3),
            'request_date_to': date(2024, 6, 3),
            'request_hour_from': 8,
            'request_hour_to': 12,
        }
        # this simulates opening a form with new employee ,
        # because here .new() creates an unsaved record with a NewId, the same thing the web client works with when you open the form before filling anything in.
        calendar_leave = self.env['hr.leave'].new(
            dict(values, work_entry_type_id=calendar_work_entry_type.id))

        working_leave = self.env['hr.leave'].new(
            dict(values, work_entry_type_id=working_work_entry_type.id))

        # in case of traceback this would fail first
        days, hours = calendar_leave._get_durations()[calendar_leave.id]
        self.assertTrue(hours, "Duration should be computed from the company calendar")
        self.assertEqual(
            (days, hours),
            working_leave._get_durations()[working_leave.id],
            "Without an employee, the duration falls back on the company calendar in both modes")

    def test_count_days_as_working_days(self):
        """Test duration calculation when count_days_as is worked days"""
        working_work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Test Time Off',
            'code': 'Test Time Off 3',
            'requires_allocation': False,
            'count_days_as': 'working',
        })
        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_hruser_id,
            'work_entry_type_id': working_work_entry_type.id,
            'request_date_from': date(2024, 6, 1),
            'request_date_to': date(2024, 6, 7),
        })

        days, hours = leave._get_durations()[leave.id]
        self.assertEqual(days, 5, "Working days should exclude weekends")
        self.assertEqual(hours, 40, "Working hours should be 5 * 8 hours")

    def test_change_count_days_as(self):
        """Changing count_days_as after leave is validated should raise ValidationError"""
        work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Test Time Off',
            'code': 'Test Time Off 4',
            'requires_allocation': False,
            'count_days_as': 'working',
        })

        work_entry_type.count_days_as = 'calendar'

        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_hruser_id,
            'work_entry_type_id': work_entry_type.id,
            'request_date_from': date(2024, 7, 1),
            'request_date_to': date(2024, 7, 5),
        })
        leave.action_approve()

        with self.assertRaises(ValidationError):
            work_entry_type.count_days_as = 'working'

    # --- _get_durations branch coverage --------------------------------------
    # _get_durations dispatches on (has an employee, count_days_as, request
    # unit) into five mutually exclusive branches. The tests above already pin
    # the employee-less branch and the whole day "calendar days" one. These pin
    # the partial day paths: the weekend adjustment of a "calendar days" leave,
    # the flexible employee shortcut, and the generic resource computation.

    def _duration_employee(self, name, resource_calendar_id=None):
        """Employee used by the duration tests, with a pinned timezone.

        The partial day computation compares `leave.date_from.date()`, which is
        UTC, with dates built from the naive `request_date_from`. Leaving the
        resource timezone to whatever the environment provides makes those two
        fall on different days depending on the machine running the test.
        """
        values = {'name': name, 'company_id': self.company.id}
        if resource_calendar_id is not None:
            values['resource_calendar_id'] = resource_calendar_id
        employee = self.env['hr.employee'].create(values)
        employee.resource_id.tz = 'Europe/Brussels'
        return employee

    def _hourly_work_entry_type(self, code, count_days_as):
        return self.env['hr.work.entry.type'].create({
            'name': code,
            'code': code,
            'requires_allocation': False,
            'count_days_as': count_days_as,
            'request_unit': 'hour',
        })

    def test_duration_partial_day_on_working_day(self):
        """A partial day on a working day: both counting modes agree.

        Wednesday 2024-06-05, 09:00 -> 12:00 Brussels, on the standard 40h/week
        schedule. "Calendar days" goes through the partial day branch, finds no
        non working day to compensate, and keeps the resource result; "working
        days" reaches the same result through the generic branch.

        The resource computation does not prorate the day: per
        `_get_attendance_intervals_days_data`, a day worth 3/4 of the theoretical
        day or less counts as half a day, above that as a full one. 3 hours is
        below 8 * 3 / 4, hence half a day for 3 hours.
        """
        calendar_leave = self.env['hr.leave'].create({
            'employee_id': self._duration_employee('Calendar Wednesday').id,
            'work_entry_type_id': self._hourly_work_entry_type('DUR_CAL_WD', 'calendar').id,
            'request_date_from': date(2024, 6, 5),
            'request_date_to': date(2024, 6, 5),
            'request_hour_from': 9,
            'request_hour_to': 12,
        })
        working_leave = self.env['hr.leave'].create({
            'employee_id': self._duration_employee('Working Wednesday').id,
            'work_entry_type_id': self._hourly_work_entry_type('DUR_WRK_WD', 'working').id,
            'request_date_from': date(2024, 6, 5),
            'request_date_to': date(2024, 6, 5),
            'request_hour_from': 9,
            'request_hour_to': 12,
        })

        self.assertEqual(calendar_leave._get_durations()[calendar_leave.id], (0.5, 3.0))
        self.assertEqual(
            working_leave._get_durations()[working_leave.id], (0.5, 3.0),
            "On a working day both counting modes give the same duration")

    def test_duration_partial_day_on_weekend(self):
        """A partial day on a Saturday: this is where the modes diverge.

        Saturday 2024-06-08 is not in the schedule, so the resource computation
        returns nothing and the entire "calendar days" duration comes from the
        non working day adjustment:

            day_hours = min(day_end, request_hour_to) - max(day_start, request_hour_from)

        with (day_start, day_end) == (8.0, 16.0), the 8h day centred on noon that
        `_get_hours_for_date(..., count_non_working_days=True)` returns for an
        employee whose calendar declares 8 hours a day. That is 12 - 9 = 3 hours.

        Note that this branch prorates the day (`day_hours / hours_per_day`,
        3 / 8 = 0.375) where the resource computation used on a working day snaps
        to a half or a full day. The very same three hour request is therefore
        worth half a day on the Wednesday and 0.375 day on the Saturday. This is
        not what the refactor introduced, it is pinned here as it stands.

        Counted as working days the same request is worth no day at all; it still
        reports its hours because the type counts as working time.
        """
        calendar_leave = self.env['hr.leave'].create({
            'employee_id': self._duration_employee('Calendar Saturday').id,
            'work_entry_type_id': self._hourly_work_entry_type('DUR_CAL_WE', 'calendar').id,
            'request_date_from': date(2024, 6, 8),
            'request_date_to': date(2024, 6, 8),
            'request_hour_from': 9,
            'request_hour_to': 12,
        })
        working_leave = self.env['hr.leave'].create({
            'employee_id': self._duration_employee('Working Saturday').id,
            'work_entry_type_id': self._hourly_work_entry_type('DUR_WRK_WE', 'working').id,
            'request_date_from': date(2024, 6, 8),
            'request_date_to': date(2024, 6, 8),
            'request_hour_from': 9,
            'request_hour_to': 12,
        })

        self.assertEqual(
            calendar_leave._get_durations()[calendar_leave.id], (0.375, 3.0),
            "Calendar days count a Saturday like any other day")
        self.assertEqual(
            working_leave._get_durations()[working_leave.id], (0, 3.0),
            "Working days count no day outside the schedule, only the hours")

    def test_duration_partial_day_flexible_employee(self):
        """A flexible employee takes the single day shortcut.

        With no working schedule the employee has no interval to intersect, so
        the duration is the requested window itself and the day count is that
        window over a 24h day: 3 / 24 = 0.125. The custom hours unit means the
        result is left unrounded.
        """
        flexible_calendar = self.env['resource.calendar'].create({
            'name': 'Flexible',
            'company_id': self.company.id,
            'calendar_type': 'undefined',
            'attendance_ids': [],
            'hours_per_week': 0,
            'hours_per_day': 0,
        })
        employee = self._duration_employee('Flexible', resource_calendar_id=flexible_calendar.id)
        self.assertTrue(
            employee.sudo()._is_flexible(),
            "This test is only meaningful for an employee without a schedule")

        leave = self.env['hr.leave'].create({
            'employee_id': employee.id,
            'work_entry_type_id': self._hourly_work_entry_type('DUR_FLEX', 'working').id,
            'request_date_from': date(2024, 6, 5),
            'request_date_to': date(2024, 6, 5),
            'request_hour_from': 9,
            'request_hour_to': 12,
        })

        self.assertEqual(leave._get_durations()[leave.id], (0.125, 3.0))
