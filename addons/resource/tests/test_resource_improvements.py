from datetime import UTC, date, datetime, timedelta

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.libs.datetime import timezone
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestSearchWorkTimeRate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar_full = cls.env["resource.calendar"].create(
            {"name": "Full Time 40h", "tz": "UTC"}
        )
        cls.calendar_part = cls.env["resource.calendar"].create(
            {"name": "Part Time 20h", "tz": "UTC"}
        )
        cls.calendar_part.attendance_ids.unlink()
        for day in range(5):
            cls.env["resource.calendar.attendance"].create(
                {
                    "name": f"Day {day}",
                    "calendar_id": cls.calendar_part.id,
                    "dayofweek": str(day),
                    "hour_from": 8,
                    "hour_to": 12,
                    "day_period": "morning",
                }
            )

    def test_search_rate_greater_than(self):
        results = self.env["resource.calendar"].search([("work_time_rate", ">", 80)])
        self.assertIn(self.calendar_full, results)
        self.assertNotIn(self.calendar_part, results)

    def test_search_rate_less_than(self):
        results = self.env["resource.calendar"].search([("work_time_rate", "<", 60)])
        self.assertIn(self.calendar_part, results)
        self.assertNotIn(self.calendar_full, results)

    def test_search_rate_in(self):
        rate = round(self.calendar_part.work_time_rate)
        results = self.env["resource.calendar"].search(
            [("work_time_rate", "in", [rate, 100])]
        )
        self.assertIn(self.calendar_full, results)


@tagged("post_install", "-at_install")
class TestCalendarWorkMethods(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env["resource.calendar"].create(
            {"name": "Standard 40h", "tz": "UTC"}
        )

    def test_works_on_date_weekday(self):
        from datetime import date

        monday = date(2025, 1, 6)
        self.assertTrue(self.calendar._works_on_date(monday))

    def test_works_on_date_weekend(self):
        from datetime import date

        saturday = date(2025, 1, 11)
        self.assertFalse(self.calendar._works_on_date(saturday))

    def test_get_hours_for_date_full_day(self):
        from datetime import date

        monday = date(2025, 1, 6)
        hour_from, hour_to = self.calendar._get_hours_for_date(monday)
        self.assertEqual(hour_from, 8.0)
        self.assertEqual(hour_to, 17.0)

    def test_get_hours_for_date_morning(self):
        from datetime import date

        monday = date(2025, 1, 6)
        hour_from, hour_to = self.calendar._get_hours_for_date(
            monday, day_period="morning"
        )
        self.assertEqual(hour_from, 8.0)
        self.assertEqual(hour_to, 12.0)

    def test_get_hours_for_date_afternoon(self):
        from datetime import date

        monday = date(2025, 1, 6)
        hour_from, hour_to = self.calendar._get_hours_for_date(
            monday, day_period="afternoon"
        )
        self.assertEqual(hour_from, 13.0)
        self.assertEqual(hour_to, 17.0)

    def test_get_hours_for_date_no_target(self):
        with self.assertRaises(ValueError):
            self.calendar._get_hours_for_date(None)

    def test_switch_based_on_duration(self):
        calendar = self.calendar
        has_lunch = calendar.attendance_ids.filtered(lambda a: a.day_period == "lunch")
        self.assertTrue(has_lunch, "Standard calendar should have lunch periods")

        calendar.switch_based_on_duration()
        self.assertTrue(calendar.duration_based)
        no_lunch = calendar.attendance_ids.filtered(lambda a: a.day_period == "lunch")
        self.assertFalse(no_lunch, "Duration mode should remove lunch periods")

        calendar.switch_based_on_duration()
        self.assertFalse(calendar.duration_based)
        has_lunch_again = calendar.attendance_ids.filtered(
            lambda a: a.day_period == "lunch"
        )
        self.assertTrue(has_lunch_again, "Disabling duration mode restores lunch")


@tagged("post_install", "-at_install")
class TestAttendanceHourConstraint(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env["resource.calendar"].create(
            {"name": "Test Calendar", "tz": "UTC"}
        )

    def test_hour_from_too_high(self):
        with self.assertRaises(ValidationError):
            self.env["resource.calendar.attendance"].create(
                {
                    "name": "Bad",
                    "calendar_id": self.calendar.id,
                    "dayofweek": "6",
                    "hour_from": 25.0,
                    "hour_to": 26.0,
                    "day_period": "morning",
                }
            )

    def test_hour_from_negative(self):
        with self.assertRaises(ValidationError):
            self.env["resource.calendar.attendance"].create(
                {
                    "name": "Bad",
                    "calendar_id": self.calendar.id,
                    "dayofweek": "6",
                    "hour_from": -1.0,
                    "hour_to": 8.0,
                    "day_period": "morning",
                }
            )

    def test_hour_from_exceeds_hour_to(self):
        with self.assertRaises(ValidationError):
            self.env["resource.calendar.attendance"].create(
                {
                    "name": "Bad",
                    "calendar_id": self.calendar.id,
                    "dayofweek": "6",
                    "hour_from": 17.0,
                    "hour_to": 8.0,
                    "day_period": "morning",
                }
            )

    def test_valid_attendance_passes(self):
        att = self.env["resource.calendar.attendance"].create(
            {
                "name": "Good",
                "calendar_id": self.calendar.id,
                "dayofweek": "6",
                "hour_from": 8.0,
                "hour_to": 12.0,
                "day_period": "morning",
            }
        )
        self.assertTrue(att.id)


@tagged("post_install", "-at_install")
class TestReservationUTCConversion(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Reservation = cls.env["resource.reservation"]
        cls.calendar = cls.env["resource.calendar"].create(
            {"name": "UTC Calendar", "tz": "UTC"}
        )
        cls.resource = cls.env["resource.resource"].create(
            {
                "name": "Test Resource",
                "calendar_id": cls.calendar.id,
            }
        )

    def test_intervals_with_non_utc_query(self):
        self.Reservation.create(
            {
                "name": "Morning slot",
                "resource_id": self.resource.id,
                "date_start": datetime(2025, 1, 6, 8, 0),
                "date_end": datetime(2025, 1, 6, 12, 0),
            }
        )
        tokyo = timezone("Asia/Tokyo")
        start = datetime(2025, 1, 6, 0, 0).replace(tzinfo=tokyo)
        end = datetime(2025, 1, 7, 0, 0).replace(tzinfo=tokyo)
        result = self.Reservation._reservation_intervals_batch(
            start, end, self.resource
        )
        intervals = list(result[self.resource.id])
        self.assertEqual(len(intervals), 1, "Should find the reservation in this range")


@tagged("post_install", "-at_install")
class TestAllocatedPercentageZero(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Reservation = cls.env["resource.reservation"]
        cls.calendar = cls.env["resource.calendar"].create(
            {"name": "UTC Calendar", "tz": "UTC"}
        )
        cls.resource = cls.env["resource.resource"].create(
            {
                "name": "Zero Resource",
                "calendar_id": cls.calendar.id,
            }
        )

    def test_zero_allocation(self):
        res = self.Reservation.create(
            {
                "name": "Zero allocation",
                "resource_id": self.resource.id,
                "date_start": datetime(2025, 1, 6, 8, 0),
                "date_end": datetime(2025, 1, 6, 17, 0),
                "allocated_percentage": 0.0,
            }
        )
        self.assertEqual(
            res.allocated_hours,
            0.0,
            "0% allocation must produce 0 hours, not fall back to 100%",
        )

    def test_fifty_percent_allocation(self):
        res = self.Reservation.create(
            {
                "name": "Half allocation",
                "resource_id": self.resource.id,
                "date_start": datetime(2025, 1, 6, 8, 0),
                "date_end": datetime(2025, 1, 6, 17, 0),
                "allocated_percentage": 50.0,
            }
        )
        self.assertEqual(res.allocated_hours, 4.0)


@tagged("post_install", "-at_install")
class TestOriginDisplayMissing(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Reservation = cls.env["resource.reservation"]
        cls.calendar = cls.env["resource.calendar"].create(
            {"name": "UTC Calendar", "tz": "UTC"}
        )
        cls.resource = cls.env["resource.resource"].create(
            {
                "name": "Display Resource",
                "calendar_id": cls.calendar.id,
            }
        )

    def test_origin_display_invalid_model(self):
        res = self.Reservation.create(
            {
                "name": "Bad origin",
                "resource_id": self.resource.id,
                "date_start": datetime(2025, 1, 6, 8, 0),
                "date_end": datetime(2025, 1, 6, 17, 0),
                "res_model": "nonexistent.model",
                "res_id": 999,
            }
        )
        self.assertEqual(res.origin_display, "nonexistent.model,999")

    def test_origin_display_no_origin(self):
        res = self.Reservation.create(
            {
                "name": "No origin",
                "resource_id": self.resource.id,
                "date_start": datetime(2025, 1, 6, 8, 0),
                "date_end": datetime(2025, 1, 6, 17, 0),
            }
        )
        self.assertFalse(res.origin_display)


@tagged("post_install", "-at_install")
class TestDSTTransition(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env["resource.calendar"].create(
            {"name": "Brussels Calendar", "tz": "Europe/Brussels"}
        )

    def test_work_hours_across_spring_forward(self):
        brussels = timezone("Europe/Brussels")
        start = datetime(2025, 3, 28, 6, 0).replace(tzinfo=brussels)
        end = datetime(2025, 3, 31, 20, 0).replace(tzinfo=brussels)
        hours = self.calendar.get_work_hours_count(start, end)
        self.assertEqual(hours, 16.0)

    def test_plan_hours_across_spring_forward(self):
        brussels = timezone("Europe/Brussels")
        start = datetime(2025, 3, 28, 8, 0).replace(tzinfo=brussels)
        result = self.calendar.plan_hours(16.0, start, compute_leaves=False)
        self.assertTrue(result, "plan_hours should find a result within range")
        if result.tzinfo:
            result_local = result.astimezone(brussels)
        else:
            result_local = result.replace(tzinfo=brussels)
        self.assertEqual(result_local.weekday(), 0, "Should land on Monday")


@tagged("post_install", "-at_install")
class TestTwoWeekCalendarEdgeCases(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env["resource.calendar"].create(
            {"name": "Standard Calendar", "tz": "UTC"}
        )

    def test_switch_to_two_weeks_and_back(self):
        original_count = len(
            self.calendar.attendance_ids.filtered(lambda a: not a.display_type)
        )
        self.assertFalse(self.calendar.two_weeks_calendar)

        self.calendar.switch_calendar_type()
        self.assertTrue(self.calendar.two_weeks_calendar)
        two_week_non_sections = self.calendar.attendance_ids.filtered(
            lambda a: not a.display_type
        )
        self.assertEqual(len(two_week_non_sections), original_count * 2)

        self.calendar.switch_calendar_type()
        self.assertFalse(self.calendar.two_weeks_calendar)

    def test_compute_two_weeks_attendance_non_two_week(self):
        self.assertFalse(self.calendar.two_weeks_calendar)
        self.assertFalse(self.calendar.attendance_ids_1st_week)
        self.assertFalse(self.calendar.attendance_ids_2nd_week)

    def test_switch_to_two_weeks_large_calendar_keeps_weeks_ordered(self):
        big = self.env["resource.calendar"].create(
            {
                "name": "Big Calendar",
                "tz": "UTC",
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": f"D{day}S{slot}",
                            "dayofweek": str(day),
                            "hour_from": 8 + slot,
                            "hour_to": 9 + slot,
                            "day_period": "morning",
                        },
                    )
                    for day in range(7)
                    for slot in range(4)
                ],
            }
        )
        self.assertEqual(len(big.attendance_ids), 28)
        big.switch_calendar_type()

        lines = big.attendance_ids
        sections = lines.filtered("display_type").sorted("sequence")
        self.assertEqual(len(sections), 2)
        first_week = lines.filtered(lambda a: not a.display_type and a.week_type == "0")
        second_week = lines.filtered(
            lambda a: not a.display_type and a.week_type == "1"
        )
        self.assertEqual(len(first_week), 28)
        self.assertEqual(len(second_week), 28)
        self.assertLess(
            max(first_week.mapped("sequence")),
            sections[1].sequence,
            "every first-week line must sort before the second-week section",
        )
        self.assertLess(
            sections[1].sequence,
            min(second_week.mapped("sequence")),
            "every second-week line must sort after its section",
        )

    def test_works_on_date_two_week_calendar(self):
        from datetime import date

        self.calendar.switch_calendar_type()
        week1_monday = self.calendar.attendance_ids.filtered(
            lambda a: a.week_type == "1" and a.dayofweek == "0" and not a.display_type
        )
        week1_monday.unlink()

        test_date = date(2025, 1, 6)
        week_type = self.env["resource.calendar.attendance"].get_week_type(test_date)
        if week_type == 1:
            self.assertFalse(self.calendar._works_on_date(test_date))
        else:
            self.assertTrue(self.calendar._works_on_date(test_date))


@tagged("post_install", "-at_install")
class TestWorksOnDateIgnoresNonWorkLines(TransactionCase):
    def test_two_week_calendar_section_rows_do_not_mark_monday(self):
        calendar = self.env["resource.calendar"].create(
            {"name": "Sections Cal", "tz": "UTC"}
        )
        calendar.switch_calendar_type()
        calendar.attendance_ids.filtered(
            lambda a: not a.display_type and a.dayofweek != "1"
        ).unlink()

        monday_w0, monday_w1 = date(2025, 1, 6), date(2025, 1, 13)
        week_types = {
            self.env["resource.calendar.attendance"].get_week_type(d)
            for d in (monday_w0, monday_w1)
        }
        self.assertEqual(week_types, {0, 1}, "consecutive Mondays span both weeks")
        for monday in (monday_w0, monday_w1):
            self.assertFalse(
                calendar._works_on_date(monday),
                "section rows must not mark Monday as worked",
            )
            self.assertTrue(calendar._works_on_date(monday + timedelta(days=1)))

    def test_lunch_only_day_is_not_working(self):
        calendar = self.env["resource.calendar"].create(
            {"name": "Lunch Cal", "tz": "UTC"}
        )
        calendar.attendance_ids.filtered(
            lambda a: a.dayofweek == "4" and a.day_period != "lunch"
        ).unlink()
        friday = date(2025, 1, 10)
        self.assertFalse(calendar._works_on_date(friday))
        self.assertTrue(calendar._works_on_date(date(2025, 1, 9)))


@tagged("post_install", "-at_install")
class TestFlexibleCalendarUnusualDays(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env["resource.calendar"].create(
            {
                "name": "Flexible 35h",
                "tz": "UTC",
                "schedule_type": "flexible",
            }
        )

    def test_unusual_days_no_leaves(self):
        start = datetime(2025, 1, 6, 0, 0).replace(tzinfo=UTC)
        end = datetime(2025, 1, 10, 23, 59).replace(tzinfo=UTC)
        result = self.calendar._get_unusual_days(start, end)
        self.assertTrue(all(not v for v in result.values()))

    def test_unusual_days_with_leave(self):
        self.env["resource.schedule.exception"].create(
            {
                "name": "Holiday",
                "calendar_id": self.calendar.id,
                "date_from": datetime(2025, 1, 8, 0, 0),
                "date_to": datetime(2025, 1, 8, 23, 59),
            }
        )
        start = datetime(2025, 1, 6, 0, 0).replace(tzinfo=UTC)
        end = datetime(2025, 1, 10, 23, 59).replace(tzinfo=UTC)
        result = self.calendar._get_unusual_days(start, end)
        self.assertTrue(result.get("2025-01-08", False))
        self.assertFalse(result.get("2025-01-06", True))


@tagged("post_install", "-at_install")
class TestFlexibleWeeklyBudgetFallback(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env["resource.calendar"].create(
            {
                "name": "Flexible 3h/day, 21h/week",
                "tz": "UTC",
                "flexible_hours": True,
                "full_time_required_hours": 21,
                "hours_per_day": 3,
            }
        )

    def test_flexible_weekly_budget_falls_back_to_ftrh(self):
        self.assertEqual(self.calendar.hours_per_week, 0.0)
        self.assertEqual(self.calendar._get_flexible_hours_per_week(), 21.0)

    def test_flexible_intervals_generated_without_hours_per_week(self):
        start = datetime(2025, 9, 1, 0, 0).replace(tzinfo=UTC)
        end = datetime(2025, 9, 14, 23, 59).replace(tzinfo=UTC)
        intervals = list(self.calendar._attendance_intervals_batch(start, end)[False])
        self.assertEqual(len(intervals), 14, "every day must get a work block")
        for interval_start, interval_end, _meta in intervals:
            hours = (interval_end - interval_start).total_seconds() / 3600
            self.assertAlmostEqual(hours, 3.0, places=6)

    def test_explicit_hours_per_week_takes_precedence(self):
        self.calendar.hours_per_week = 10.0
        self.assertEqual(self.calendar._get_flexible_hours_per_week(), 10.0)


@tagged("post_install", "-at_install")
class TestPlanHoursWithResource(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env["resource.calendar"].create(
            {"name": "Test Calendar", "tz": "UTC"}
        )
        cls.resource = cls.env["resource.resource"].create(
            {
                "name": "Worker",
                "calendar_id": cls.calendar.id,
                "tz": "UTC",
            }
        )

    def test_plan_hours_with_resource_leave(self):
        self.env["resource.schedule.exception"].create(
            {
                "name": "Sick day",
                "calendar_id": self.calendar.id,
                "resource_id": self.resource.id,
                "date_from": datetime(2025, 1, 7, 0, 0),
                "date_to": datetime(2025, 1, 7, 23, 59),
            }
        )
        start = datetime(2025, 1, 6, 8, 0).replace(tzinfo=UTC)
        result = self.calendar.plan_hours(
            16.0, start, compute_leaves=True, resource=self.resource
        )
        self.assertTrue(result)
        self.assertEqual(result.weekday(), 2)
        self.assertEqual(result.hour, 17)

    def test_plan_hours_negative(self):
        start = datetime(2025, 1, 8, 17, 0).replace(tzinfo=UTC)
        result = self.calendar.plan_hours(-8.0, start, compute_leaves=False)
        self.assertTrue(result)
        self.assertEqual(result.hour, 8)
        self.assertEqual(result.day, 8)

    def test_plan_hours_zero(self):
        start = datetime(2025, 1, 6, 10, 0).replace(tzinfo=UTC)
        self.assertEqual(
            self.calendar.plan_hours(0.0, start, compute_leaves=False), start
        )

    def test_plan_hours_zero_outside_working_time(self):
        saturday = datetime(2025, 1, 11, 10, 0).replace(tzinfo=UTC)
        monday_start = datetime(2025, 1, 13, 8, 0).replace(tzinfo=UTC)
        self.assertEqual(
            self.calendar.plan_hours(0.0, saturday, compute_leaves=False), monday_start
        )
        self.assertEqual(
            self.calendar.plan_hours(0.0002, saturday, compute_leaves=False).replace(
                microsecond=0
            ),
            monday_start,
        )


@tagged("post_install", "-at_install")
class TestListWorkTimePerDay(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env["resource.calendar"].create(
            {"name": "Standard", "tz": "UTC"}
        )

    def test_get_unusual_days_fixed_calendar(self):
        start = datetime(2025, 1, 6, 0, 0).replace(tzinfo=UTC)
        end = datetime(2025, 1, 12, 23, 59).replace(tzinfo=UTC)
        result = self.calendar._get_unusual_days(start, end)
        self.assertTrue(result.get("2025-01-11", False), "Saturday should be unusual")
        self.assertTrue(result.get("2025-01-12", False), "Sunday should be unusual")
        self.assertFalse(result.get("2025-01-06", True), "Monday should be normal")

    def test_get_unusual_days_keeps_the_last_day_on_an_early_end_time(self):
        start = datetime(2025, 1, 6, 8, 0).replace(tzinfo=UTC)
        end = datetime(2025, 1, 8, 0, 0).replace(tzinfo=UTC)
        result = self.calendar._get_unusual_days(start, end)
        self.assertIn("2025-01-08", result)


@tagged("post_install", "-at_install")
class TestDurationBasedAverageHours(TransactionCase):
    def test_duration_based_average_hours(self):
        calendar = self.env["resource.calendar"].create(
            {
                "name": "Duration based Calendar",
                "attendance_ids": False,
                "duration_based": True,
            }
        )
        for dow, name in (("0", "Mon"), ("1", "Tue"), ("2", "Wed")):
            self.env["resource.calendar.attendance"].create(
                {
                    "name": name,
                    "calendar_id": calendar.id,
                    "dayofweek": dow,
                    "day_period": "full_day",
                    "duration_hours": 4.0,
                }
            )
        self.assertEqual(calendar.hours_per_week, 12)
        self.assertEqual(calendar.hours_per_day, 4)

    def test_non_duration_based_uses_hour_bounds(self):
        calendar = self.env["resource.calendar"].create(
            {"name": "Hour based Calendar", "attendance_ids": False}
        )
        for dow, name in (("0", "Mon"), ("1", "Tue"), ("2", "Wed")):
            self.env["resource.calendar.attendance"].create(
                {
                    "name": name,
                    "calendar_id": calendar.id,
                    "dayofweek": dow,
                    "day_period": "full_day",
                    "hour_from": 8,
                    "hour_to": 16,
                }
            )
        self.assertEqual(calendar.hours_per_week, 24)
        self.assertEqual(calendar.hours_per_day, 8)


@tagged("post_install", "-at_install")
class TestFullDayMidpointSplit(TransactionCase):
    def test_full_day_split_uses_midpoint(self):
        from datetime import date

        calendar = self.env["resource.calendar"].create(
            {"name": "Late shift", "tz": "UTC", "attendance_ids": False}
        )
        self.env["resource.calendar.attendance"].create(
            {
                "name": "Mon",
                "calendar_id": calendar.id,
                "dayofweek": "0",
                "day_period": "full_day",
                "hour_from": 10,
                "hour_to": 18,
            }
        )
        monday = date(2025, 1, 6)
        self.assertEqual(
            calendar._get_hours_for_date(monday, day_period="morning"),
            (10.0, 14.0),
        )
        self.assertEqual(
            calendar._get_hours_for_date(monday, day_period="afternoon"),
            (14.0, 18.0),
        )


@tagged("post_install", "-at_install")
class TestDurationHoursClearedBounds(TransactionCase):
    def test_duration_zeroed_when_hours_cleared(self):
        calendar = self.env["resource.calendar"].create(
            {"name": "Clear Cal", "tz": "UTC"}
        )
        attendance = calendar.attendance_ids.filtered(
            lambda a: a.day_period == "morning"
        )[0]
        self.assertGreater(attendance.duration_hours, 0)
        attendance.write({"hour_from": 0.0, "hour_to": 0.0})
        self.assertEqual(
            attendance.duration_hours,
            0.0,
            "clearing the bounds must not leave a stale duration",
        )


@tagged("post_install", "-at_install")
class TestLeaveCompanyFallback(TransactionCase):
    def test_leave_company_follows_resource(self):
        company_b = self.env["res.company"].create({"name": "Company B"})
        resource_b = self.env["resource.resource"].create(
            {
                "name": "B worker",
                "company_id": company_b.id,
                "calendar_id": False,
                "tz": "UTC",
            }
        )
        leave = self.env["resource.schedule.exception"].create(
            {
                "name": "B leave",
                "resource_id": resource_b.id,
                "date_from": datetime(2025, 1, 6, 0, 0),
                "date_to": datetime(2025, 1, 6, 23, 59),
            }
        )
        self.assertFalse(leave.calendar_id)
        self.assertEqual(
            leave.company_id,
            company_b,
            "the resource's company must beat the acting company",
        )


@tagged("post_install", "-at_install")
class TestDurationHoursRecompute(TransactionCase):
    def test_duration_hours_recomputed_on_day_period_change(self):
        calendar = self.env["resource.calendar"].create(
            {"name": "Recompute calendar", "attendance_ids": False}
        )
        attendance = self.env["resource.calendar.attendance"].create(
            {
                "name": "Lunch then work",
                "calendar_id": calendar.id,
                "dayofweek": "0",
                "day_period": "lunch",
                "hour_from": 8,
                "hour_to": 16,
            }
        )
        self.assertEqual(attendance.duration_hours, 0)
        attendance.day_period = "full_day"
        self.assertEqual(attendance.duration_hours, 8)


@tagged("post_install", "-at_install")
class TestDurationDaysDepends(TransactionCase):
    def test_duration_days_recomputes_on_hours_change(self):
        calendar = self.env["resource.calendar"].create(
            {"name": "Duration-days depends", "tz": "UTC"}
        )
        attendance = self.env["resource.calendar.attendance"].create(
            {
                "name": "Sat AM",
                "calendar_id": calendar.id,
                "dayofweek": "5",
                "hour_from": 8,
                "hour_to": 10,
                "day_period": "morning",
            }
        )
        self.assertEqual(attendance.duration_days, 0.5)

        attendance.hour_to = 18

        self.assertEqual(
            attendance.duration_days,
            1.0,
            "duration_days must follow duration_hours, not stay stale.",
        )

    def test_duration_days_recomputes_on_calendar_hours_change(self):
        calendar = self.env["resource.calendar"].create(
            {
                "name": "hours-per-day leg",
                "tz": "UTC",
                "attendance_ids": [
                    Command.create(
                        {
                            "name": "Mon AM",
                            "dayofweek": "0",
                            "hour_from": 8,
                            "hour_to": 14,
                            "day_period": "morning",
                        }
                    ),
                    Command.create(
                        {
                            "name": "Mon PM",
                            "dayofweek": "0",
                            "hour_from": 14,
                            "hour_to": 16,
                            "day_period": "afternoon",
                        }
                    ),
                ],
            }
        )
        target = calendar.attendance_ids.filtered(lambda a: a.name == "Mon AM")
        filler = calendar.attendance_ids.filtered(lambda a: a.name == "Mon PM")
        self.assertEqual(calendar.hours_per_day, 8)
        self.assertEqual(target.duration_days, 0.5)

        filler.hour_to = 15

        self.assertEqual(calendar.hours_per_day, 7)
        self.assertEqual(
            target.duration_days,
            1.0,
            "duration_days must follow calendar_id.hours_per_day, not only its own hours.",
        )
