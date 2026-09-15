from collections import defaultdict
from datetime import UTC, datetime

from freezegun import freeze_time

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestCalendarIntegrity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Calendar = cls.env["resource.calendar"]
        cls.Attendance = cls.env["resource.calendar.attendance"]

    def _line(self, calendar, dayofweek):
        return calendar.attendance_ids.filtered(
            lambda a: a.dayofweek == dayofweek and a.day_period == "morning"
        )

    def test_copying_a_flexible_calendar_keeps_its_weekly_total(self):
        flexible = self.Calendar.create(
            {
                "name": "Flexible",
                "flexible_hours": True,
                "hours_per_week": 30,
                "hours_per_day": 6,
            }
        )
        copy = flexible.copy()
        self.assertEqual(copy.hours_per_week, 30)
        self.assertEqual(copy.hours_per_day, 6)

    def test_copying_with_new_lines_recomputes_the_totals(self):
        source = self.Calendar.create({"name": "Full time"})
        self.assertEqual(source.hours_per_week, 40)
        half = source.copy(
            {
                "attendance_ids": [
                    Command.create(
                        {
                            "name": f"Day {day}",
                            "dayofweek": day,
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        }
                    )
                    for day in "01234"
                ]
            }
        )
        self.assertEqual(half.hours_per_week, 20)
        self.assertEqual(half.hours_per_day, 4)
        self.assertEqual(set(half.attendance_ids.mapped("duration_days")), {1.0})

    def test_schedule_type_is_a_view_of_flexible_hours(self):
        flexible = self.Calendar.create({"name": "F", "schedule_type": "flexible"})
        self.assertTrue(flexible.flexible_hours)
        fixed = self.Calendar.create({"name": "X"})
        self.assertEqual(fixed.schedule_type, "fully_fixed")
        fixed.flexible_hours = True
        self.assertEqual(fixed.schedule_type, "flexible")
        fixed.schedule_type = "fully_fixed"
        self.assertFalse(fixed.flexible_hours)
        self.assertEqual(
            self.Calendar.search_count([("flexible_hours", "=", True)]),
            1
            + self.Calendar.search_count(
                [("flexible_hours", "=", True), ("id", "not in", [flexible.id])]
            ),
        )

    def test_overlap_is_rejected_when_a_line_is_written_directly(self):
        calendar = self.Calendar.create({"name": "Fixed"})
        with self.assertRaises(ValidationError):
            self._line(calendar, "0").write({"hour_to": 16})

    def test_overlap_is_rejected_when_a_line_is_created_directly(self):
        calendar = self.Calendar.create({"name": "Fixed"})
        with self.assertRaises(ValidationError):
            self.Attendance.create(
                {
                    "calendar_id": calendar.id,
                    "name": "Clash",
                    "dayofweek": "1",
                    "hour_from": 9,
                    "hour_to": 11,
                    "day_period": "morning",
                }
            )

    def test_overlap_is_rejected_when_a_line_moves_to_another_day(self):
        calendar = self.Calendar.create({"name": "Fixed"})
        saturday = self.Attendance.create(
            {
                "calendar_id": calendar.id,
                "name": "Saturday",
                "dayofweek": "5",
                "hour_from": 8,
                "hour_to": 12,
                "day_period": "morning",
            }
        )
        with self.assertRaises(ValidationError):
            saturday.dayofweek = "0"

    def test_weekly_totals_follow_a_period_change(self):
        calendar = self.Calendar.create({"name": "Fixed"})
        self.assertEqual(calendar.hours_per_week, 40)
        lunch = calendar.attendance_ids.filtered(lambda a: a.day_period == "lunch")[0]
        lunch.write({"day_period": "morning", "hour_from": 7, "hour_to": 8})
        self.assertEqual(calendar.hours_per_week, 41)
        self.assertEqual(calendar.hours_per_day, 8.2)

    def test_weekly_totals_follow_a_section_change(self):
        calendar = self.Calendar.create({"name": "Fixed"})
        self._line(calendar, "0").display_type = "line_section"
        self.assertEqual(calendar.hours_per_week, 36)

    def test_weekly_totals_follow_duration_based_switch(self):
        calendar = self.Calendar.create({"name": "Fixed"})
        calendar.switch_based_on_duration()
        calendar.attendance_ids[0].duration_hours = 2
        self.assertEqual(calendar.hours_per_week, 38)

    def test_two_weeks_flag_requires_week_type_on_every_line(self):
        calendar = self.Calendar.create({"name": "Fixed"})
        with self.assertRaises(ValidationError):
            calendar.two_weeks_calendar = True

    def test_switching_back_to_one_week_under_a_two_weeks_company_default(self):
        company_calendar = self.env.company.resource_calendar_id
        company_calendar.switch_calendar_type()
        calendar = self.Calendar.create({"name": "Follower"})
        self.assertTrue(calendar.two_weeks_calendar)
        calendar.switch_calendar_type()
        self.assertFalse(calendar.two_weeks_calendar)
        self.assertFalse(calendar.attendance_ids.filtered("display_type"))
        self.assertEqual(set(calendar.attendance_ids.mapped("week_type")), {False})
        self.assertEqual(calendar.hours_per_week, 40)

    def test_duration_switch_under_a_two_weeks_company_default(self):
        company_calendar = self.env.company.resource_calendar_id
        company_calendar.switch_calendar_type()
        calendar = self.Calendar.create({"name": "Follower"})
        calendar.switch_based_on_duration()
        calendar.switch_based_on_duration()
        lines = calendar.attendance_ids.filtered(lambda a: not a.display_type)
        self.assertEqual(len(lines), 30)
        self.assertEqual(set(lines.mapped("week_type")), {"0", "1"})
        self.assertEqual(calendar.hours_per_week, 40)

    def test_break_on_duration_based_calendar_is_a_validation_error(self):
        calendar = self.Calendar.create({"name": "Duration"})
        calendar.switch_based_on_duration()
        with self.assertRaises(ValidationError):
            self.Attendance.create(
                {
                    "calendar_id": calendar.id,
                    "name": "Break",
                    "dayofweek": "5",
                    "hour_from": 12,
                    "hour_to": 13,
                    "day_period": "lunch",
                }
            )

    def test_two_weeks_split_views_follow_line_edits(self):
        calendar = self.Calendar.create({"name": "Fixed"})
        calendar.switch_calendar_type()
        first_before = len(calendar.attendance_ids_1st_week)
        line = self.Attendance.create(
            {
                "calendar_id": calendar.id,
                "name": "Saturday",
                "dayofweek": "5",
                "hour_from": 8,
                "hour_to": 12,
                "day_period": "morning",
                "week_type": "1",
            }
        )
        self.assertEqual(len(calendar.attendance_ids_1st_week), first_before)
        line.week_type = "0"
        self.assertEqual(len(calendar.attendance_ids_1st_week), first_before + 1)


@tagged("post_install", "-at_install")
class TestCompanyCalendarCreation(TransactionCase):
    def test_a_shared_calendar_chosen_as_default_stays_shared(self):
        shared = self.env["resource.calendar"].create(
            {"name": "Shared", "company_id": False}
        )
        company = self.env["res.company"].create(
            {"name": "Newco", "resource_calendar_id": shared.id}
        )
        self.assertEqual(company.resource_calendar_id, shared)
        self.assertFalse(shared.company_id)

    def test_a_company_without_a_default_gets_its_own(self):
        company = self.env["res.company"].create({"name": "Newco"})
        self.assertEqual(company.resource_calendar_id.company_id, company)


@tagged("post_install", "-at_install")
class TestLeaveDefaults(TransactionCase):
    def test_default_dates_use_the_calendar_date_not_the_utc_date(self):
        calendar = self.env["resource.calendar"].create(
            {"name": "Mexico", "tz": "America/Mexico_City"}
        )
        with freeze_time("2026-09-06 04:30:00"):
            defaults = (
                self.env["resource.schedule.exception"]
                .with_context(default_calendar_id=calendar.id)
                .default_get(["date_from", "date_to", "calendar_id"])
            )
        self.assertEqual(defaults["date_from"], datetime(2026, 9, 5, 6, 0))
        self.assertEqual(defaults["date_to"], datetime(2026, 9, 6, 5, 59, 59, 999999))


@tagged("post_install", "-at_install")
class TestBatchedResourceQueries(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Resource = cls.env["resource.resource"]
        cls.fixed = cls.env.company.resource_calendar_id
        cls.flexible = cls.env["resource.calendar"].create(
            {"name": "Flexible", "flexible_hours": True, "hours_per_week": 30}
        )
        cls.fixed_resources = Resource.create(
            [
                {"name": f"fixed {i}", "calendar_id": cls.fixed.id, "tz": "UTC"}
                for i in range(10)
            ]
        )
        cls.flexible_resources = Resource.create(
            [
                {"name": f"flex {i}", "calendar_id": cls.flexible.id, "tz": "UTC"}
                for i in range(10)
            ]
        )
        cls.env["resource.schedule.exception"].create(
            [
                {
                    "name": "off",
                    "resource_id": resource.id,
                    "calendar_id": resource.calendar_id.id,
                    "date_from": datetime(2026, 9, 8),
                    "date_to": datetime(2026, 9, 8, 23, 59, 59),
                }
                for resource in (cls.fixed_resources | cls.flexible_resources)[::3]
            ]
        )
        cls.start = datetime(2026, 9, 7, tzinfo=UTC)
        cls.stop = datetime(2026, 9, 14, tzinfo=UTC)

    def _count(self, fn):
        self.env.flush_all()
        self.env.invalidate_all()
        before = self.env.cr.sql_statement_count
        result = fn()
        return self.env.cr.sql_statement_count - before, result

    def test_adjust_to_calendar_is_batched_per_calendar(self):
        one, _ = self._count(
            lambda: self.fixed_resources[0]._adjust_to_calendar(self.start, self.stop)
        )
        many, result = self._count(
            lambda: self.fixed_resources._adjust_to_calendar(self.start, self.stop)
        )
        self.assertLessEqual(many, one + 2)
        for resource in self.fixed_resources:
            self.assertEqual(
                result[resource],
                resource._adjust_to_calendar(self.start, self.stop)[resource],
            )

    def test_unavailable_intervals_of_flexible_resources_are_batched(self):
        one, _ = self._count(
            lambda: self.flexible._unavailable_intervals_batch(
                self.start, self.stop, self.flexible_resources[0]
            )
        )
        many, result = self._count(
            lambda: self.flexible._unavailable_intervals_batch(
                self.start, self.stop, self.flexible_resources
            )
        )
        self.assertLessEqual(many, one + 2)
        self.assertEqual(len(result), len(self.flexible_resources))
        self.assertEqual(len(result[self.flexible_resources[2].id]), 1)
        self.assertEqual(result[self.flexible_resources[1].id], [])

    def test_unavailable_intervals_mixed_batch_matches_singles(self):
        resources = self.fixed_resources[:3] | self.flexible_resources[:3]
        batch = self.fixed._unavailable_intervals_batch(
            self.start, self.stop, resources
        )
        for resource in resources:
            single = self.fixed._unavailable_intervals_batch(
                self.start, self.stop, resource
            )
            self.assertEqual(batch[resource.id], single[resource.id])


@tagged("post_install", "-at_install")
class TestOverlapSweepInSql(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.resource = cls.env["resource.resource"].create(
            {"name": "Lathe", "tz": "UTC"}
        )
        cls.Reservation = cls.env["resource.reservation"]
        cls.booked = cls.Reservation.create(
            {
                "name": "booked",
                "resource_id": cls.resource.id,
                "date_start": datetime(2026, 6, 1, 8),
                "date_end": datetime(2026, 6, 1, 12),
                "allocated_percentage": 60,
            }
        )

    def test_prospective_conflicts_accept_string_datetimes(self):
        conflicts = self.Reservation._prospective_conflicts(
            [
                {
                    "resource_id": self.resource.id,
                    "date_start": "2026-06-01 10:00:00",
                    "date_end": "2026-06-01 11:00:00",
                    "allocated_percentage": 50,
                }
            ]
        )
        self.assertEqual(conflicts, self.booked)

    def test_prospective_within_capacity_is_not_a_conflict(self):
        conflicts = self.Reservation._prospective_conflicts(
            [
                {
                    "resource_id": self.resource.id,
                    "date_start": datetime(2026, 6, 1, 10),
                    "date_end": datetime(2026, 6, 1, 11),
                    "allocated_percentage": 40,
                }
            ]
        )
        self.assertFalse(conflicts)

    def test_search_operators_agree_with_the_compute(self):
        other = self.Reservation.create(
            {
                "name": "clash",
                "resource_id": self.resource.id,
                "date_start": datetime(2026, 6, 1, 9),
                "date_end": datetime(2026, 6, 1, 10),
            }
        )
        self.assertEqual(self.booked.schedule_overlap_count, 1)
        self.assertEqual(
            self.Reservation.search([("schedule_overlap_count", ">=", 1)]),
            self.booked | other,
        )
        self.assertNotIn(
            self.booked, self.Reservation.search([("schedule_overlap_count", "<", 1)])
        )


@tagged("post_install", "-at_install")
class TestWorkSchedule(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Resource = cls.env["resource.resource"]
        cls.fixed_calendar = cls.env.company.resource_calendar_id
        cls.fixed_calendar.tz = "UTC"
        flexible_calendar = cls.env["resource.calendar"].create(
            {
                "name": "Flexible 20h",
                "flexible_hours": True,
                "hours_per_week": 20,
                "hours_per_day": 4,
                "tz": "UTC",
            }
        )
        cls.fixed = Resource.create(
            {"name": "fixed", "calendar_id": cls.fixed_calendar.id, "tz": "UTC"}
        )
        cls.flexible = Resource.create(
            {"name": "flexible", "calendar_id": flexible_calendar.id, "tz": "UTC"}
        )
        cls.free = Resource.create({"name": "free", "calendar_id": False, "tz": "UTC"})
        cls.env["resource.schedule.exception"].create(
            {
                "name": "off",
                "resource_id": cls.fixed.id,
                "calendar_id": cls.fixed_calendar.id,
                "date_from": datetime(2026, 6, 2),
                "date_to": datetime(2026, 6, 2, 23, 59, 59),
            }
        )
        cls.start = datetime(2026, 6, 1, tzinfo=UTC)
        cls.stop = datetime(2026, 6, 6, tzinfo=UTC)

    def test_one_call_covers_every_kind_of_resource(self):
        resources = self.fixed | self.flexible | self.free
        schedule = resources._get_work_schedule(self.start, self.stop)
        self.assertEqual(set(schedule.intervals), set(resources.ids))
        self.assertEqual(schedule.flexible_ids, {self.flexible.id, self.free.id})
        self.assertEqual(schedule.work_hours(self.fixed), 32)
        self.assertEqual(schedule.work_hours(self.flexible), 20)
        self.assertEqual(schedule.work_hours(self.free), 120)

    def test_a_resource_outside_the_schedule_reads_as_empty(self):
        schedule = self.fixed._get_work_schedule(self.start, self.stop)
        self.assertEqual(len(schedule.intervals[self.flexible.id]), 0)
        self.assertEqual(schedule.work_hours(self.flexible), 0)

    def test_schedule_agrees_with_the_two_apis_it_replaces(self):
        schedule = (self.fixed | self.flexible)._get_work_schedule(
            self.start, self.stop
        )
        fixed_intervals, _calendars = self.fixed._get_valid_work_intervals(
            self.start, self.stop
        )
        self.assertEqual(
            list(schedule.intervals[self.fixed.id]),
            list(fixed_intervals[self.fixed.id]),
        )
        intervals, per_day, per_week = (
            self.flexible._get_flexible_resource_valid_work_intervals(
                self.start, self.stop
            )
        )
        self.assertEqual(
            schedule.work_hours(self.flexible),
            self.flexible._get_flexible_resource_work_hours(
                intervals[self.flexible.id],
                per_day[self.flexible.id],
                per_week[self.flexible.id],
            ),
        )

    def test_compute_leaves_is_honoured_for_fixed_resources(self):
        with_leaves = self.fixed._get_work_schedule(self.start, self.stop)
        without = self.fixed._get_work_schedule(
            self.start, self.stop, compute_leaves=False
        )
        self.assertEqual(with_leaves.work_hours(self.fixed), 32)
        self.assertEqual(without.work_hours(self.fixed), 40)

    def test_work_hours_per_day_is_filled_for_both_kinds(self):
        schedule = (self.fixed | self.flexible)._get_work_schedule(
            self.start, self.stop
        )
        fixed_days = defaultdict(float)
        schedule.work_hours(self.fixed, work_hours_per_day=fixed_days)
        self.assertEqual(sum(fixed_days.values()), 32)
        self.assertNotIn(datetime(2026, 6, 2).date(), fixed_days)
        flexible_days = defaultdict(float)
        schedule.work_hours(self.flexible, work_hours_per_day=flexible_days)
        self.assertEqual(sum(flexible_days.values()), 20)
