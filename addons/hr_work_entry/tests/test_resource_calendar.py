from datetime import UTC, date, datetime

from odoo.fields import Date
from odoo.tests import TransactionCase, new_test_user


class TestResourceCalendarLeaveTypedLine(TransactionCase):
    """A schedule line typed as time off is not work time.

    ``_get_global_attendances`` already says so -- it is what makes
    ``hours_per_week`` drop -- but the interval side had never been told, so
    the same calendar answered "32 hours a week" and "Friday is a working day".
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env["resource.calendar"].create(
            {"name": "Four days and a Friday off", "tz": "UTC"}
        )
        cls.unpaid = cls.env.ref("hr_work_entry.work_entry_type_unpaid_leave")
        cls.fridays = cls.calendar.attendance_ids.filtered(
            lambda attendance: attendance.dayofweek == "4"
        )
        # A full Monday-to-Sunday week, so the assertions read as weekdays.
        cls.monday = datetime(2026, 8, 31, tzinfo=UTC)
        cls.sunday = datetime(2026, 9, 6, 23, 59, tzinfo=UTC)
        cls.friday = date(2026, 9, 4)

    def _unusual_days(self):
        return self.calendar._get_unusual_days(self.monday, self.sunday)

    def _worked_dates(self, **kwargs):
        return {
            interval[0].date()
            for interval in self.calendar._work_intervals_batch(
                self.monday, self.sunday, **kwargs
            )[False]
        }

    def test_leave_typed_line_stops_being_work_time(self):
        self.assertFalse(self._unusual_days()[Date.to_string(self.friday)])
        self.assertIn(self.friday, self._worked_dates())

        self.fridays.work_entry_type_id = self.unpaid
        self.calendar.invalidate_recordset()

        self.assertEqual(
            self.calendar._get_hours_per_week(),
            32.0,
            "the hours side already excluded the line",
        )
        self.assertTrue(
            self._unusual_days()[Date.to_string(self.friday)],
            "and the calendar has to agree with it",
        )
        self.assertNotIn(self.friday, self._worked_dates())

    def test_flexible_resource_keeps_its_availability(self):
        """A resource with no calendar is available all week regardless.

        Its intervals carry a dummy attendance rather than a real line, so
        nothing about the calendar's typing may reach them. Upstream needs a
        guard in ``resource`` for the same reason.
        """
        self.fridays.work_entry_type_id = self.unpaid
        flexible = self.env["resource.resource"].create(
            {
                "name": "No calendar of their own",
                "calendar_id": False,
                "tz": "UTC",
                "company_id": self.env.company.id,
            }
        )
        intervals = self.calendar._work_intervals_batch(
            self.monday, self.sunday, resources=flexible
        )[flexible.id]
        self.assertEqual(len(intervals), 7)

    def test_a_plain_user_can_still_read_the_schedule(self):
        """`mrp`, `project` and `hr_calendar` reach this for ordinary users.

        ``work_entry_type_id`` is behind ``hr.group_hr_user``, so reading it
        unsudoed here would raise AccessError in modules that have nothing to
        do with payroll.
        """
        self.fridays.work_entry_type_id = self.unpaid
        joe = new_test_user(self.env, login="joe_no_hr", groups="base.group_user")
        self.assertFalse(joe.has_group("hr.group_hr_user"))
        self.assertNotIn(self.friday, self._worked_dates())
        calendar = self.calendar.with_user(joe)
        worked = {
            interval[0].date()
            for interval in calendar._work_intervals_batch(self.monday, self.sunday)[
                False
            ]
        }
        self.assertNotIn(self.friday, worked)
