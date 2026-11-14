# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from odoo.tests import Form, TransactionCase, freeze_time, tagged

USER_TZ = 'Europe/Brussels'


def utc(day, hour=0, minute=0, tz=USER_TZ):
    local = datetime.combine(day, time.min, ZoneInfo(tz)) + timedelta(hours=hour, minutes=minute)
    return local.astimezone(UTC).replace(tzinfo=None)


@tagged('post_install', '-at_install', 'belam')
class TestAttendanceDefaultShift(TransactionCase):
    """Default check in / out proposed when a day cell is clicked in the calendar or gantt view."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Calendar = cls.env['resource.calendar']
        cls.calendar_8h = cls.env.ref('resource.resource_calendar_std')
        cls.calendar_two_slots = Calendar.create({
            'name': 'Two slots',
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {'dayofweek': str(day), 'hour_from': hour_from, 'hour_to': hour_to})
                for day in range(5) for hour_from, hour_to in ((8, 12), (13, 17))
            ],
        })
        cls.calendar_nine_to_five = Calendar.create({
            'name': '9-17',
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {'dayofweek': str(day), 'hour_from': 9, 'hour_to': 17}) for day in range(5)
            ],
        })
        cls.calendar_flexible = Calendar.create({
            'name': 'Flexible', 'calendar_type': 'undefined', 'hours_per_day': 7.6, 'hours_per_week': 38,
        })
        cls.calendar_fully_flexible = Calendar.create({
            'name': 'Fully flexible', 'calendar_type': 'undefined', 'hours_per_day': 0, 'hours_per_week': 0,
        })

        # A week outside the daylight saving time transitions
        cls.monday = date(2026, 11, 9)
        cls.wednesday = cls.monday + timedelta(days=2)
        cls.saturday = cls.monday + timedelta(days=5)

    def _employee(self, calendar, tz=USER_TZ):
        return self.env['hr.employee'].create({'name': calendar.name, 'tz': tz, 'resource_calendar_id': calendar.id})

    def _default_shift(self, employee, day, start_hour=0, stop_hour=24, all_day=True, tz=USER_TZ):
        """Open a new attendance form as a view does when a day cell is clicked.

        The gantt view sends the whole day (00:00 -> 24:00), the calendar view 07:00 -> 19:00,
        both in the browser's timezone ``tz``, and the clicked day.
        """
        context = {
            'tz': tz,
            'default_employee_id': employee.id,
            'default_check_in': str(utc(day, start_hour, tz=tz)),
            'default_check_out': str(utc(day, stop_hour, tz=tz)),
        }
        if all_day:
            context.update(isAllDay=True, allDayDate=str(day))
        form = Form(self.env['hr.attendance'].with_context(context))
        return form.check_in, form.check_out

    def test_first_planned_slot(self):
        """ If there are multiple slots in the employee's agenda for a specific day, we pick the first one. """
        employee = self._employee(self.calendar_8h)
        self.assertEqual(self._default_shift(employee, self.wednesday), (utc(self.wednesday, 8), utc(self.wednesday, 16)))

        employee = self._employee(self.calendar_two_slots)
        self.assertEqual(
            self._default_shift(employee, self.wednesday), (utc(self.wednesday, 8), utc(self.wednesday, 12)),
            "Only the first slot of the day is proposed")

    def test_gantt_and_calendar_ranges(self):
        """ Calendar view and gantt view should return the same default values """
        employee = self._employee(self.calendar_two_slots)
        self.assertEqual(
            self._default_shift(employee, self.wednesday, start_hour=7, stop_hour=19),
            self._default_shift(employee, self.wednesday),
            "The calendar (07:00 -> 19:00) and the gantt (whole day) give the same shift")

    def test_flexible_hours(self):
        """ If flexible hours, we use the average hours per day, centered around noon."""
        employee = self._employee(self.calendar_flexible)
        self.assertEqual(
            self._default_shift(employee, self.wednesday),
            (utc(self.wednesday, 8, 12), utc(self.wednesday, 15, 48)))

    def test_no_planned_slot(self):
        """ If no planned slot for that day, we use the average hours per day, centered around noon. """
        employee = self._employee(self.calendar_two_slots)
        self.assertEqual(
            self._default_shift(employee, self.saturday), (utc(self.saturday, 8), utc(self.saturday, 16)),
            "Without a planned slot, the average day is centered on noon")

        self.env['resource.calendar.leaves'].create({
            'name': 'Leave',
            'calendar_id': self.calendar_two_slots.id,
            'resource_id': employee.resource_id.id,
            'date_from': utc(self.wednesday, 0),
            'date_to': utc(self.wednesday, 24),
        })
        self.assertEqual(
            self._default_shift(employee, self.wednesday), (utc(self.wednesday, 8), utc(self.wednesday, 16)),
            "A day of absence has no planned slot")

    def test_no_average_hours(self):
        """ If no average hour, the default slot starts at 7am and has a duration of 0 """
        employee = self._employee(self.calendar_fully_flexible)
        check_in, check_out = self._default_shift(employee, self.wednesday)
        self.assertEqual((check_in, check_out), (utc(self.wednesday, 7), utc(self.wednesday, 7)))
        attendance = self.env['hr.attendance'].create({
            'employee_id': employee.id, 'check_in': check_in, 'check_out': check_out,
        })
        self.assertEqual(attendance.worked_hours, 0)

    def test_version_calendar(self):
        """ We use the version that is valid for the attendance date. """
        # Today is Monday 9 November 2026: the current version is the 8h one
        with freeze_time(self.monday):
            # From 1 January 2026: 8h calendar (08:00 -> 16:00)
            employee = self._employee(self.calendar_8h)
            employee.version_id.write({'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1)})
            # From Wednesday 11 November 2026: two slots calendar (08:00 -> 12:00, 13:00 -> 17:00)
            employee.create_version({'date_version': self.wednesday, 'resource_calendar_id': self.calendar_two_slots.id})
            # Monday 9 November 2026
            self.assertEqual(
                self._default_shift(employee, self.monday), (utc(self.monday, 8), utc(self.monday, 16)),
                "Before Wednesday, the 8h calendar of the previous version is used")
            # Wednesday 11 November 2026
            self.assertEqual(
                self._default_shift(employee, self.wednesday), (utc(self.wednesday, 8), utc(self.wednesday, 12)),
                "The calendar of the version in effect on the clicked day is used, not the current one")

    def test_employee_in_another_timezone(self):
        """ The employee timezone is computed when the attendance is created.
        So that the user can be warned if there's a mismatch that can lead to confusion. """
        employee = self._employee(self.calendar_nine_to_five, tz='America/New_York')
        check_in, check_out = self._default_shift(employee, self.wednesday)
        self.assertEqual(
            (check_in, check_out), (utc(self.wednesday, 15), utc(self.wednesday, 23)),
            "The real hours of the employee: 09:00 -> 17:00 in New York")

        attendance = self.env['hr.attendance'].create({
            'employee_id': employee.id, 'check_in': check_in, 'check_out': check_out,
        })
        self.assertEqual(attendance.employee_tz, 'America/New_York',
                        msg="The attendance.employee_tz should match the employee timezone")

    def test_clicked_day_in_employee_timezone(self):
        """ The attendance is created with the employee timezone, even though it may be
        timezone translated in the user's browser."""
        sydney = 'Australia/Sydney'
        employee = self._employee(self.calendar_8h, tz=sydney)
        self.assertEqual(
            self._default_shift(employee, self.wednesday),
            (utc(self.wednesday, 8, tz=sydney), utc(self.wednesday, 16, tz=sydney)),
            "Wednesday in Sydney, which starts on Tuesday in Brussels")
        self.assertEqual(
            self._default_shift(employee, self.wednesday, tz=sydney),
            (utc(self.wednesday, 8, tz=sydney), utc(self.wednesday, 16, tz=sydney)),
            "The browser's timezone does not matter")

        new_york = 'America/New_York'
        employee = self._employee(self.calendar_fully_flexible, tz=new_york)
        self.assertEqual(
            self._default_shift(employee, self.wednesday),
            (utc(self.wednesday, 7, tz=new_york), utc(self.wednesday, 7, tz=new_york)),
            "The fallback is at 07:00 for the employee")

    def test_without_all_day(self):
        employee = self._employee(self.calendar_two_slots)
        self.assertEqual(
            self._default_shift(employee, self.wednesday, start_hour=9, stop_hour=11, all_day=False),
            (utc(self.wednesday, 9), utc(self.wednesday, 11)),
            "A time slot selection is kept as is")
