from datetime import UTC, datetime

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestDeletingAScheduleDoesNotCreateAGlobalHoliday(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Calendar = cls.env["resource.calendar"]
        cls.Resource = cls.env["resource.resource"]
        cls.Leave = cls.env["resource.schedule.exception"]
        cls.start = datetime(2026, 6, 1, tzinfo=UTC)
        cls.stop = datetime(2026, 6, 6, tzinfo=UTC)

    def _bystander(self):
        return self.Calendar.create({"name": "Bystander schedule"})

    def test_deleting_a_schedule_does_not_widen_its_time_off(self):
        bystander = self._bystander()
        doomed = self.Calendar.create({"name": "Doomed schedule"})
        self.Leave.create(
            {
                "name": "Doomed team offsite",
                "calendar_id": doomed.id,
                "date_from": datetime(2026, 6, 3, 0, 0),
                "date_to": datetime(2026, 6, 3, 23, 59),
            }
        )
        self.env.flush_all()
        before = bystander.get_work_hours_count(self.start, self.stop)

        doomed.attendance_ids.unlink()
        doomed.unlink()
        self.env.flush_all()
        bystander.invalidate_recordset()

        self.assertEqual(
            bystander.get_work_hours_count(self.start, self.stop),
            before,
            "an unrelated schedule lost a day because a deleted schedule's time off"
            " kept a NULL calendar_id, which _leave_intervals_batch reads as"
            " 'applies to every calendar'",
        )

    def test_deleting_a_calendarless_resource_does_not_widen_its_time_off(self):
        """A resource with a calendar is safe: the leave keeps ``calendar_id``
        and stays scoped to it.  The leak needs BOTH columns to go NULL, which
        is what happens to a fully flexible resource -- the shape the form
        offers as "Fully Flexible" and the default for a bare material asset.
        """
        bystander = self._bystander()
        machine = self.Resource.create(
            {
                "name": "Lathe #3",
                "resource_type": "material",
                "calendar_id": False,
                "tz": "UTC",
            }
        )
        self.env.flush_all()
        self.Leave.create(
            {
                "name": "Lathe maintenance",
                "resource_id": machine.id,
                "date_from": datetime(2026, 6, 4, 0, 0),
                "date_to": datetime(2026, 6, 4, 23, 59),
            }
        )
        self.env.flush_all()
        before = bystander.get_work_hours_count(self.start, self.stop)

        machine.unlink()
        self.env.flush_all()
        bystander.invalidate_recordset()

        self.assertEqual(
            bystander.get_work_hours_count(self.start, self.stop),
            before,
            "an unrelated schedule lost a day because a deleted resource's personal"
            " time off kept a NULL resource_id AND a NULL calendar_id, which"
            " _leave_intervals_batch reads as 'applies to everything'",
        )

    def test_deleting_a_resource_that_has_a_calendar_is_already_safe(self):
        """Pins the boundary, so the fix is not credited with more than it does."""
        bystander = self._bystander()
        own = self.Calendar.create({"name": "Machine shift"})
        self.env.flush_all()
        machine = self.Resource.create(
            {
                "name": "Press #1",
                "resource_type": "material",
                "calendar_id": own.id,
                "tz": "UTC",
            }
        )
        self.env.flush_all()
        self.Leave.create(
            {
                "name": "Press maintenance",
                "resource_id": machine.id,
                "date_from": datetime(2026, 6, 4, 0, 0),
                "date_to": datetime(2026, 6, 4, 23, 59),
            }
        )
        self.env.flush_all()
        before = bystander.get_work_hours_count(self.start, self.stop)
        machine.unlink()
        self.env.flush_all()
        bystander.invalidate_recordset()
        self.assertEqual(bystander.get_work_hours_count(self.start, self.stop), before)

    def test_a_genuinely_global_leave_still_applies_everywhere(self):
        """The counterpart: cascading must not take the real wildcard with it."""
        bystander = self._bystander()
        before = bystander.get_work_hours_count(self.start, self.stop)
        self.Leave.create(
            {
                "name": "Public holiday",
                "calendar_id": False,
                "date_from": datetime(2026, 6, 3, 0, 0),
                "date_to": datetime(2026, 6, 3, 23, 59),
            }
        )
        self.env.flush_all()
        bystander.invalidate_recordset()
        self.assertLess(
            bystander.get_work_hours_count(self.start, self.stop),
            before,
            "a leave declared with no calendar is the real wildcard and must keep"
            " reaching every schedule",
        )


@tagged("post_install", "-at_install")
class TestAFlexibleScheduleIsNeverSilentlyEmpty(TransactionCase):
    """``hours_per_day`` gates the weekly budget and is never computed for a
    flexible calendar, so a schedule born flexible allocates zero hours however
    large its weekly total says it is."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Calendar = cls.env["resource.calendar"]
        cls.start = datetime(2026, 6, 1, tzinfo=UTC)
        cls.stop = datetime(2026, 6, 8, tzinfo=UTC)

    def test_created_flexible_with_a_weekly_total_yields_that_total(self):
        calendar = self.Calendar.create(
            {"name": "Consultants", "schedule_type": "flexible", "hours_per_week": 40}
        )
        self.env.flush_all()
        self.assertTrue(calendar.flexible_hours)
        self.assertGreater(
            calendar.get_work_hours_count(self.start, self.stop),
            0.0,
            "a flexible schedule declaring 40 hours a week allocated none, because"
            " hours_per_day was never computed and gates the weekly budget",
        )

    def test_clearing_the_daily_average_does_not_empty_the_schedule(self):
        calendar = self.Calendar.create({"name": "Consultants 2"})
        self.env.flush_all()
        calendar.write({"schedule_type": "flexible", "hours_per_day": 0.0})
        self.env.flush_all()
        self.assertGreater(
            calendar.get_work_hours_count(self.start, self.stop),
            0.0,
            "clearing the editable, non-required Avg field emptied the schedule",
        )


@tagged("post_install", "-at_install")
class TestTheTwoFlexibleWeekModelsDisagree(TransactionCase):
    """Two weekly-budget models coexist and neither is wrong on its own.

    ``resource.calendar._flexible_attendance_intervals`` fills a *rolling*
    seven-day window anchored at the caller's start, pinned by
    ``TestFlexibleAttendanceSynthesis.test_seven_day_window_yields_the_weekly_budget``.
    ``resource.resource._get_flexible_resource_valid_work_intervals`` caps per
    *ISO calendar week*, pinned by ``TestFlexibleWeekKeyIsDeterministic``.

    Both pins are deliberate, so flipping either is a product decision rather
    than a repair -- and the last attempt to make the calendar side ISO broke
    six subtests of the first pin, whose own message anticipates exactly that
    edit.  What is not a decision is that the disagreement is silent: it lands
    on ``resource.reservation.allocated_hours``, a stored field, and only for a
    flexible resource.  This test states the two numbers so the gap cannot widen
    unnoticed, and so whoever settles it has the measurement in front of them.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env["resource.calendar"].create(
            {
                "name": "Flexible 40h",
                "schedule_type": "flexible",
                "hours_per_week": 40,
                "hours_per_day": 8,
                "tz": "UTC",
            }
        )
        cls.resource = cls.env["resource.resource"].create(
            {"name": "Flexy", "calendar_id": cls.calendar.id, "tz": "UTC"}
        )
        # Wednesday to Wednesday: one rolling week, but two ISO weeks.
        cls.start = datetime(2026, 6, 3)
        cls.stop = datetime(2026, 6, 10)

    def test_three_readings_agree_on_the_rolling_window(self):
        aware = (self.start.replace(tzinfo=UTC), self.stop.replace(tzinfo=UTC))
        by_calendar = self.calendar.get_work_hours_count(*aware)
        with_resource = sum(
            (stop - start).total_seconds() / 3600
            for start, stop, _meta in self.calendar._attendance_intervals_batch(
                *aware, resources=self.resource
            )[self.resource.id]
        )
        valid, _calendars = self.resource._get_valid_work_intervals(*aware)
        by_resource = sum(
            (stop - start).total_seconds() / 3600
            for start, stop, _m in valid[self.resource.id]
        )
        self.assertAlmostEqual(by_calendar, 40.0, places=2)
        self.assertAlmostEqual(with_resource, 40.0, places=2)
        self.assertAlmostEqual(by_resource, 40.0, places=2)

    def test_allocated_hours_is_the_one_reading_that_differs(self):
        reservation = self.env["resource.reservation"].create(
            {
                "name": "Sprint",
                "resource_id": self.resource.id,
                "date_start": self.start,
                "date_end": self.stop,
            }
        )
        self.env.flush_all()
        self.assertAlmostEqual(
            reservation.allocated_hours,
            56.0,
            places=2,
            msg="allocated_hours goes through _scheduling_get_work_hours, the only"
            " reading that caps per ISO week; 40.0 here means the models were"
            " unified and this test should be deleted with the decision recorded",
        )

    def test_a_fixed_calendar_has_no_such_gap(self):
        fixed = self.env["resource.calendar"].create({"name": "Fixed", "tz": "UTC"})
        resource = self.env["resource.resource"].create(
            {"name": "Fixy", "calendar_id": fixed.id, "tz": "UTC"}
        )
        reservation = self.env["resource.reservation"].create(
            {
                "name": "Sprint",
                "resource_id": resource.id,
                "date_start": self.start,
                "date_end": self.stop,
            }
        )
        self.env.flush_all()
        self.assertAlmostEqual(
            reservation.allocated_hours,
            fixed.get_work_hours_count(
                self.start.replace(tzinfo=UTC), self.stop.replace(tzinfo=UTC)
            ),
            places=2,
        )
