from datetime import UTC, date, datetime

from odoo.fields import Command, Domain
from odoo.libs.datetime import timezone
from odoo.tests.common import TransactionCase


class TestResourceCalendar(TransactionCase):
    def test_fully_flexible_attendance_interval_duration(self):
        calendar = self.env["resource.calendar"].create(
            {
                "name": "Standard Calendar",
                "two_weeks_calendar": False,
            }
        )
        resource = self.env["resource.resource"].create(
            {
                "name": "Wade Wilson",
                "calendar_id": False,
                "tz": "America/New_York",
            }
        )
        self.env["resource.calendar.attendance"].create(
            {
                "name": "TEMP",
                "calendar_id": calendar.id,
                "dayofweek": "5",
                "hour_from": 14,
                "hour_to": 17,
            }
        )
        UTC = timezone("UTC")
        start_dt = datetime(2025, 6, 4, 18, 0, 0).astimezone(UTC)
        end_dt = datetime(2025, 6, 4, 21, 0, 0).astimezone(UTC)
        result_per_resource_id = calendar._attendance_intervals_batch(
            start_dt, end_dt, resource
        )
        start, end, attendance = result_per_resource_id[resource.id]._items[0]
        self.assertEqual(
            start, start_dt, "Output start time should match the input start time"
        )
        self.assertEqual(end, end_dt, "Output end time should match the input end time")
        self.assertEqual(
            attendance.duration_hours, 3.0, "Attendance duration should be 3 hours"
        )
        self.assertAlmostEqual(
            attendance.duration_days,
            3.0 / calendar.hours_per_day,
            places=6,
            msg="3 hours is 3/hours_per_day of a working day. This asserted a flat"
            " 0.125 -- 3/24 -- back when a fully-flexible day was modelled as 24"
            " wall-clock hours, which is the same modelling that made a Mon-Fri"
            " absence measure 4.375 days instead of 5.",
        )

    def test_flexible_calendar_attendance_interval_duration(self):
        flexible_calendar = self.env["resource.calendar"].create(
            {
                "name": "Flexible Calendar",
                "hours_per_day": 7.0,
                "hours_per_week": 30,
                "full_time_required_hours": 30,
                "flexible_hours": True,
                "tz": "UTC",
            }
        )

        expected_hours = [7, 7, 7, 7, 2]

        start_dt = datetime(2025, 6, 2, 0, 0, 0).astimezone(UTC)
        end_dt = datetime(2025, 6, 7, 23, 59, 59).astimezone(UTC)
        result_per_resource_id = flexible_calendar._attendance_intervals_batch(
            start_dt, end_dt
        )
        self.assertEqual(
            expected_hours,
            [
                (end - start).total_seconds() / 3600
                for start, end, dummy_attendance in result_per_resource_id[0]._items
            ],
        )
        self.assertEqual(
            expected_hours,
            [
                dummy_attendance.duration_hours
                for start, end, dummy_attendance in result_per_resource_id[0]._items
            ],
        )

        start_dt = datetime(2025, 6, 2, 11, 0, 0).astimezone(UTC)
        end_dt = datetime(2025, 6, 7, 13, 0, 0).astimezone(UTC)
        result_per_resource_id = flexible_calendar._attendance_intervals_batch(
            start_dt, end_dt
        )

        self.assertTrue(
            start_dt <= result_per_resource_id[0]._items[0][0],
            "First attendance interval should not start before start_dt",
        )
        self.assertTrue(
            end_dt >= result_per_resource_id[0]._items[4][1],
            "Last attendance interval should not end after end_dt",
        )

    def test_flexible_calendar_days_data_without_hours_per_day(self):
        bare = self.env["resource.calendar"].create(
            {
                "name": "Bare Flexible Calendar",
                "flexible_hours": True,
                "tz": "UTC",
            }
        )
        self.assertEqual(bare.hours_per_day, 0.0)

        start_dt = datetime(2025, 6, 2, 0, 0, 0).astimezone(UTC)
        end_dt = datetime(2025, 6, 6, 23, 59, 59).astimezone(UTC)
        intervals = bare._attendance_intervals_batch(start_dt, end_dt)[0]
        data = bare._get_attendance_intervals_days_data(intervals)
        self.assertGreater(data["hours"], 0.0)
        self.assertGreater(data["days"], 0.0)

    def test_domain_filters_the_records_the_path_reads(self):
        calendar = self.env["resource.calendar"].create(
            {
                "name": "9-to-5",
                "tz": "UTC",
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Morning",
                            "dayofweek": str(i),
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    )
                    for i in range(5)
                ]
                + [
                    (
                        0,
                        0,
                        {
                            "name": "Afternoon",
                            "dayofweek": str(i),
                            "hour_from": 13,
                            "hour_to": 17,
                            "day_period": "afternoon",
                        },
                    )
                    for i in range(5)
                ],
            }
        )
        start_dt = datetime(2026, 6, 1, 0, 0, 0).astimezone(UTC)
        end_dt = datetime(2026, 6, 5, 23, 59, 59).astimezone(UTC)
        without_domain = calendar.get_work_hours_count(
            start_dt, end_dt, compute_leaves=False
        )
        with_domain = calendar.get_work_hours_count(
            start_dt,
            end_dt,
            compute_leaves=False,
            domain=[("day_period", "=", "morning")],
        )
        self.assertEqual(
            without_domain,
            with_domain,
            "get_work_hours_count reads leaves only, so its domain has nothing"
            " to filter when compute_leaves=False.",
        )
        # get_work_duration_data's domain filters the ATTENDANCES on that path:
        # hr_payroll splits a calendar by `work_entry_type_id` through it to
        # count out-of-contract days, so dropping it here reads the whole
        # calendar into every such count.
        self.assertEqual(
            calendar.get_work_duration_data(
                start_dt,
                end_dt,
                compute_leaves=False,
                domain=[("day_period", "=", "morning")],
            )["hours"],
            without_domain / 2,
        )

    def test_attendance_duration_data_filters_the_attendances(self):
        calendar = self.env["resource.calendar"].create(
            {
                "name": "9-to-5",
                "tz": "UTC",
                "attendance_ids": [
                    Command.create(
                        {
                            "name": period.capitalize(),
                            "dayofweek": str(day),
                            "hour_from": hour_from,
                            "hour_to": hour_from + 4,
                            "day_period": period,
                        }
                    )
                    for day in range(5)
                    for period, hour_from in (("morning", 8), ("afternoon", 13))
                ],
            }
        )
        start_dt = datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC)
        end_dt = datetime(2026, 6, 5, 23, 59, 59, tzinfo=UTC)

        everything = calendar.get_attendance_duration_data(start_dt, end_dt)
        mornings = calendar.get_attendance_duration_data(
            start_dt, end_dt, domain=[("day_period", "=", "morning")]
        )

        self.assertEqual(everything["hours"], 40.0)
        self.assertEqual(mornings["hours"], 20.0)

    def test_flexible_self_does_not_override_a_fixed_resource_calendar(self):
        fixed = self.env["resource.calendar"].create(
            {
                "name": "9-to-5 with lunch",
                "tz": "UTC",
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": f"{period}",
                            "dayofweek": str(i),
                            "hour_from": hour_from,
                            "hour_to": hour_to,
                            "day_period": period,
                        },
                    )
                    for i in range(5)
                    for period, hour_from, hour_to in (
                        ("morning", 9, 12),
                        ("lunch", 12, 13),
                        ("afternoon", 13, 17),
                    )
                ],
            }
        )
        resource = self.env["resource.resource"].create(
            {"name": "On fixed calendar", "calendar_id": fixed.id, "tz": "UTC"}
        )
        flexible_self = self.env["resource.calendar"].create(
            {
                "name": "Flexible fallback",
                "flexible_hours": True,
                "hours_per_day": 8.0,
                "full_time_required_hours": 40.0,
                "tz": "UTC",
            }
        )
        start_dt = datetime(2026, 6, 1, 0, 0, 0).astimezone(UTC)
        end_dt = datetime(2026, 6, 6, 23, 59, 59).astimezone(UTC)

        via_own_calendar = fixed._attendance_intervals_batch(
            start_dt, end_dt, resource
        )[resource.id]
        via_flexible_self = flexible_self._attendance_intervals_batch(
            start_dt, end_dt, resource
        )[resource.id]
        self.assertEqual(len(via_flexible_self), len(via_own_calendar))

        lunch_via_own_calendar = fixed._attendance_intervals_batch(
            start_dt, end_dt, resource, lunch=True
        )[resource.id]
        lunch_via_flexible_self = flexible_self._attendance_intervals_batch(
            start_dt, end_dt, resource, lunch=True
        )[resource.id]
        self.assertEqual(len(lunch_via_flexible_self), len(lunch_via_own_calendar))

    def test_flexible_partial_day_is_a_fraction_not_a_whole_day(self):
        fixed = self.env["resource.calendar"].create(
            {
                "name": "9-to-5 (measuring calendar)",
                "tz": "UTC",
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Morning",
                            "dayofweek": str(i),
                            "hour_from": 9,
                            "hour_to": 17,
                            "day_period": "morning",
                        },
                    )
                    for i in range(5)
                ],
            }
        )
        flexible = self.env["resource.calendar"].create(
            {
                "name": "Flexible, tight weekly cap",
                "flexible_hours": True,
                "hours_per_day": 8.0,
                "full_time_required_hours": 10,
                "tz": "UTC",
            }
        )
        resource = self.env["resource.resource"].create(
            {"name": "On flexible calendar", "calendar_id": flexible.id, "tz": "UTC"}
        )
        start_dt = datetime(2026, 6, 1, 0, 0, 0).astimezone(UTC)
        end_dt = datetime(2026, 6, 3, 23, 59, 59).astimezone(UTC)
        intervals = fixed._attendance_intervals_batch(start_dt, end_dt, resource)[
            resource.id
        ]
        data = fixed._get_attendance_intervals_days_data(intervals)
        self.assertEqual(data["hours"], 10.0)
        self.assertEqual(data["days"], 1.25)

    def test_public_holiday_calendar_no_company(self):
        self.env["resource.schedule.exception"].create(
            [
                {
                    "name": "Public Holiday for company",
                    "company_id": self.env.company.id,
                    "date_from": datetime(2019, 5, 29, 0, 0, 0),
                    "date_to": datetime(2019, 5, 30, 0, 0, 0),
                    "resource_id": False,
                }
            ]
        )
        calendar = self.env["resource.calendar"].create(
            {
                "name": "40 hours/week",
                "hours_per_day": 8,
                "full_time_required_hours": 40,
            }
        )
        calendar.company_id = False
        date_from = datetime(2019, 5, 27, 0, 0, 0).astimezone(UTC)
        date_to = datetime(2019, 5, 31, 23, 59, 59).astimezone(UTC)
        days = calendar._get_unusual_days(date_from, date_to, self.env.company)
        expected_res = {
            "2019-05-27": False,
            "2019-05-28": False,
            "2019-05-29": True,
            "2019-05-30": False,
            "2019-05-31": False,
        }
        self.assertEqual(days, expected_res)

    def test_public_holidays_domain_scopes_by_window_company_and_calendar(self):
        company_a, company_b = self.env["res.company"].create(
            [{"name": "Holidays A"}, {"name": "Holidays B"}]
        )
        calendar_a, calendar_other = self.env["resource.calendar"].create(
            [
                {"name": "A", "company_id": company_a.id},
                {"name": "Other", "company_id": company_a.id},
            ]
        )
        resource = self.env["resource.resource"].create(
            {"name": "Someone", "company_id": company_a.id}
        )
        Leaves = self.env["resource.schedule.exception"]

        def holiday(company, day, **vals):
            return Leaves.with_company(company).create(
                {
                    "name": f"{company.name} {day} {vals}",
                    "date_from": datetime(2030, 5, day, 8),
                    "date_to": datetime(2030, 5, day, 17),
                    **vals,
                }
            )

        every_calendar = holiday(company_a, 1)
        own_calendar = holiday(company_a, 2, calendar_id=calendar_a.id)
        other_calendar = holiday(company_a, 3, calendar_id=calendar_other.id)
        other_company = holiday(company_b, 1)
        personal = holiday(company_a, 1, resource_id=resource.id)
        fixtures = (
            every_calendar | own_calendar | other_calendar | other_company | personal
        )

        def found(date_from, date_to, **scope):
            return Leaves.search(
                Leaves._get_domain_public_holidays(date_from, date_to, **scope)
                & Domain("id", "in", fixtures.ids)
            )

        window = (datetime(2030, 5, 1), datetime(2030, 5, 4))
        self.assertEqual(
            found(*window, companies=company_a, calendars=calendar_a),
            every_calendar | own_calendar,
        )
        self.assertEqual(
            found(*window, companies=company_a),
            every_calendar | own_calendar | other_calendar,
        )
        self.assertEqual(
            found(*window),
            every_calendar | own_calendar | other_calendar | other_company,
        )
        self.assertEqual(
            found(
                datetime(2030, 5, 1, 17), datetime(2030, 5, 2, 8), companies=company_a
            ),
            every_calendar | own_calendar,
            "a window touching a holiday's edge overlaps it",
        )
        self.assertEqual(
            found(date(2030, 4, 30), date(2030, 5, 1), companies=company_a),
            every_calendar,
            "a date bound covers its whole day",
        )
