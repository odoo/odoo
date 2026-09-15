from datetime import date, datetime, timedelta
from unittest.mock import patch

import pytz

from odoo import Command, fields
from odoo.tests.common import TransactionCase, tagged


def _slots(with_lunch):
    for day in range(7):
        yield Command.create(
            {
                "name": f"morning {day}",
                "dayofweek": str(day),
                "hour_from": 9,
                "hour_to": 12 if with_lunch else 16,
                "day_period": "morning",
            }
        )
        if not with_lunch:
            continue
        yield Command.create(
            {
                "name": f"lunch {day}",
                "dayofweek": str(day),
                "hour_from": 12,
                "hour_to": 13,
                "day_period": "lunch",
            }
        )
        yield Command.create(
            {
                "name": f"afternoon {day}",
                "dayofweek": str(day),
                "hour_from": 13,
                "hour_to": 17,
                "day_period": "afternoon",
            }
        )


OFFICE_ZONE = "Europe/Brussels"


class ScheduleZoneCase(TransactionCase):
    """Employees who work the office's schedule in another time zone.

    Every calendar here is written in the office's zone and every employee is
    deployed in the zone under test, so a reader that interprets the schedule in
    the calendar's zone instead of the employee's work zone is caught.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create(
            {
                "name": "Split Zones Ltd",
                "auto_check_out": True,
                "auto_check_out_tolerance": 1.0,
            }
        )

    def _calendar(self, tz, with_lunch=True):
        calendar = self.env["resource.calendar"].create(
            {
                "name": f"9-17 worked in {tz}",
                "tz": OFFICE_ZONE,
                "company_id": self.company.id,
                "flexible_hours": False,
                "hours_per_day": 7 if with_lunch else 9,
                "attendance_ids": [Command.clear(), *_slots(with_lunch)],
            }
        )
        self._work_zones[calendar] = tz
        return calendar

    def setUp(self):
        super().setUp()
        self._work_zones = {}

    def _employee(self, calendar, work_tz=None, **extra):
        return self.env["hr.employee"].create(
            {
                "name": f"Works {calendar.tz}",
                "company_id": self.company.id,
                "resource_calendar_id": calendar.id,
                "date_version": date(2020, 1, 1),
                "contract_date_start": date(2020, 1, 1),
                "tz": work_tz or self._work_zones.get(calendar, calendar.tz),
                **extra,
            }
        )

    @staticmethod
    def _utc(tz, moment):
        return (
            pytz.timezone(tz).localize(moment).astimezone(pytz.UTC).replace(tzinfo=None)
        )


@tagged("post_install", "-at_install")
class TestWorkedHoursDeductsTheLunchBreak(ScheduleZoneCase):
    def test_the_break_is_deducted_in_every_zone(self):
        """A nine-hour presence against a schedule carrying an hour of lunch is
        eight worked hours, whatever zone the schedule is written in.

        The span was localised in the SCHEDULE's zone and the break in the
        RESOURCE's, so for any employee whose two zones differ by more than the
        break is long the break landed outside the span and was deducted from
        nothing.
        """
        for tz in ("UTC", "Asia/Tokyo", "Pacific/Honolulu", "America/Mexico_City"):
            with self.subTest(tz=tz):
                employee = self._employee(self._calendar(tz))
                attendance = self.env["hr.attendance"].create(
                    {
                        "employee_id": employee.id,
                        "check_in": self._utc(tz, datetime(2026, 9, 7, 9, 0)),
                        "check_out": self._utc(tz, datetime(2026, 9, 7, 18, 0)),
                    }
                )
                self.assertAlmostEqual(attendance.worked_hours, 8.0, 3)

    def test_a_schedule_without_a_break_deducts_nothing(self):
        employee = self._employee(self._calendar("Asia/Tokyo", with_lunch=False))
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": employee.id,
                "check_in": self._utc("Asia/Tokyo", datetime(2026, 9, 7, 9, 0)),
                "check_out": self._utc("Asia/Tokyo", datetime(2026, 9, 7, 18, 0)),
            }
        )
        self.assertAlmostEqual(attendance.worked_hours, 9.0, 3)


@tagged("post_install", "-at_install")
class TestTheDayIsTheVersionsDay(ScheduleZoneCase):
    def test_a_later_schedule_change_does_not_re_date_a_past_attendance(self):
        """`date` is the day in the employee's work zone, which a later schedule
        change does not move."""
        tokyo = self._calendar("Asia/Tokyo", with_lunch=False)
        honolulu = self._calendar("Pacific/Honolulu", with_lunch=False)
        employee = self._employee(tokyo)
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": employee.id,
                # 2026-09-08 07:00 in Tokyo, still 2026-09-07 in Honolulu.
                "check_in": datetime(2026, 9, 7, 22, 0),
                "check_out": datetime(2026, 9, 8, 6, 0),
            }
        )
        self.assertEqual(attendance.date, date(2026, 9, 8))

        employee.create_version(
            {
                "date_version": date(2026, 9, 12),
                "resource_calendar_id": honolulu.id,
            }
        )
        self.env.flush_all()
        attendance.invalidate_recordset(["date"])
        attendance.modified(["check_in"])
        self.env.flush_all()

        self.assertEqual(
            attendance.date,
            date(2026, 9, 8),
            "the day belongs to the schedule the employee was on when they "
            "worked it, not the one they are on now",
        )
        self.assertEqual(attendance.date, attendance._local_date_span()[0])


@tagged("post_install", "-at_install")
class TestAutoCheckOutIsZoneIndependent(ScheduleZoneCase):
    def _close(self, tz):
        employee = self._employee(self._calendar(tz))
        check_in = self._utc(tz, datetime(2026, 9, 7, 9, 0))
        attendance = self.env["hr.attendance"].create(
            {"employee_id": employee.id, "check_in": check_in}
        )
        now = self._utc(tz, datetime(2026, 9, 7, 23, 0))
        with patch.object(fields.Datetime, "now", staticmethod(lambda: now)):
            self.env["hr.attendance"]._cron_auto_check_out()
        attendance.invalidate_recordset()
        return attendance

    def test_the_same_overrun_is_cut_at_the_same_worked_hour_everywhere(self):
        """Seven scheduled hours plus an hour of tolerance is eight worked
        hours, in every zone.

        The cut used to be placed by subtracting the excess from
        `check_in.replace(hour=23, minute=59, second=59)` -- the end of the
        check-in's UTC day, not of the employee's -- so the same overrun on the
        same schedule was cut an hour apart from one zone to the next. The
        comparison that decided to cut at all counted the employee's lunch as
        expected work while the placement did not count it as worked.
        """
        for tz in ("UTC", "Asia/Tokyo", "Pacific/Honolulu", "America/Mexico_City"):
            with self.subTest(tz=tz):
                attendance = self._close(tz)
                self.assertEqual(attendance.out_mode, "auto_check_out")
                self.assertAlmostEqual(attendance.worked_hours, 8.0, 3)

    def test_the_cut_lands_on_the_same_wall_clock_everywhere(self):
        for tz in ("UTC", "Asia/Tokyo", "Pacific/Honolulu", "America/Mexico_City"):
            with self.subTest(tz=tz):
                attendance = self._close(tz)
                local = pytz.UTC.localize(attendance.check_out).astimezone(
                    pytz.timezone(tz)
                )
                self.assertEqual(local.strftime("%Y-%m-%d %H:%M"), "2026-09-07 18:00")

    def test_hours_already_worked_that_day_come_off_the_budget(self):
        tz = "Asia/Tokyo"
        employee = self._employee(self._calendar(tz))
        self.env["hr.attendance"].create(
            {
                "employee_id": employee.id,
                "check_in": self._utc(tz, datetime(2026, 9, 7, 6, 0)),
                "check_out": self._utc(tz, datetime(2026, 9, 7, 8, 0)),
            }
        )
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": employee.id,
                "check_in": self._utc(tz, datetime(2026, 9, 7, 9, 0)),
            }
        )
        now = self._utc(tz, datetime(2026, 9, 7, 23, 0))
        with patch.object(fields.Datetime, "now", staticmethod(lambda: now)):
            self.env["hr.attendance"]._cron_auto_check_out()
        attendance.invalidate_recordset()
        self.assertAlmostEqual(
            attendance.worked_hours,
            6.0,
            3,
            "two hours were already worked that local day, so six of the "
            "eight-hour budget are left. The earlier attendance opened before "
            "the check-in's naive-UTC midnight and used to fall outside the "
            "window this is read from.",
        )


@tagged("post_install", "-at_install")
class TestScheduledHoursExcludeTheBreak(ScheduleZoneCase):
    def test_a_lunch_line_is_not_expected_work(self):
        employee = self._employee(self._calendar("Asia/Tokyo"))
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": employee.id,
                "check_in": self._utc("Asia/Tokyo", datetime(2026, 9, 7, 9, 0)),
            }
        )
        self.assertAlmostEqual(
            attendance._scheduled_hours_on(date(2026, 9, 7)),
            7.0,
            3,
            "9-12 and 13-17 is seven hours of work; the 12-13 lunch line is "
            "not one of them",
        )


@tagged("post_install", "-at_install")
class TestFlexibleResourceKeepsItsHours(ScheduleZoneCase):
    """A flexible employee keeps no scheduled break, so nothing is deducted.

    `resource.calendar._attendance_intervals_batch` answers per resource, and
    for a FLEXIBLE resource its answer is the whole span -- that resource may
    work at any time. Read as "the lunch break" it removes every worked hour
    the attendance has. The company's calendar is not a fallback here either:
    an employee with no schedule of their own does not take the company's
    lunch.
    """

    def _worked(self, setup, flexible, calendar_tz="Asia/Tokyo"):
        employee = self._employee(self._calendar(calendar_tz))
        setup(employee)
        self.env.flush_all()
        self.env.invalidate_all()
        # Assert the fixture before the behaviour: if clearing a calendar stops
        # making a resource flexible, these tests would read nine hours for
        # another reason entirely and pass without touching the guard.
        self.assertEqual(
            employee.resource_id._is_flexible(),
            flexible,
            "the fixture does not describe the case this test is about",
        )
        return (
            self.env["hr.attendance"]
            .create(
                {
                    "employee_id": employee.id,
                    "check_in": self._utc(calendar_tz, datetime(2026, 9, 7, 9, 0)),
                    "check_out": self._utc(calendar_tz, datetime(2026, 9, 7, 18, 0)),
                }
            )
            .worked_hours
        )

    def test_a_resource_with_no_calendar_keeps_every_hour(self):
        self.assertAlmostEqual(
            self._worked(lambda e: e.resource_id.write({"calendar_id": False}), True),
            9.0,
            3,
            "nine hours of presence, no schedule to take a break from",
        )

    def test_a_version_with_no_calendar_keeps_every_hour(self):
        self.assertAlmostEqual(
            self._worked(lambda e: e.write({"resource_calendar_id": False}), True),
            9.0,
            3,
            "the company's calendar is not a schedule this employee works to; "
            "reading it here deducted the company's lunch, and reading it "
            "through the flexible resource deducted the entire nine hours",
        )

    def test_a_calendar_marked_flexible_keeps_every_hour(self):
        flexible = self._calendar("Asia/Tokyo")
        flexible.flexible_hours = True
        self.assertAlmostEqual(
            self._worked(
                lambda e: e.write({"resource_calendar_id": flexible.id}), True
            ),
            9.0,
            3,
        )

    def test_a_scheduled_employee_still_loses_the_break(self):
        self.assertAlmostEqual(
            self._worked(lambda e: None, False),
            8.0,
            3,
            "the control: without it these three pass against a break that is "
            "never deducted for anybody",
        )


@tagged("post_install", "-at_install")
class TestADayIsNotAlwaysTwentyFourHours(ScheduleZoneCase):
    """The day window `_scheduled_hours_on` asks about reaches the next local
    midnight, so it tiles a day that is not 24 hours long.

    Where the clocks go back at midnight the local day has 25 hours and its
    last hour repeats; `datetime.combine(day, time.max)` resolves to the first
    of the two. Measured over twelve zones and every day of 2026, a window
    ending there leaves 3600s of America/Santiago 2026-04-04 and of
    Asia/Beirut 2026-10-24 outside it, and a window ending at the next local
    midnight leaves nothing anywhere.

    The assertion is on the WINDOW and not on the hours returned, because the
    hours do not move: `_attendance_intervals_batch` materialises each calendar
    line once per calendar day and does not model the repeated hour from either
    window. Asserting the hours would be asserting a difference that does not
    exist -- 0.983h comes back from both.
    """

    LONG_DAY = date(2026, 4, 4)  # America/Santiago: 23:00 happens twice
    ZONE = "America/Santiago"

    def _window_asked_for(self, local_day):
        seen = []
        batch = type(self.env["resource.calendar"])._attendance_intervals_batch

        def spy(calendar, start, stop, *args, **kwargs):
            seen.append((start, stop))
            return batch(calendar, start, stop, *args, **kwargs)

        employee = self._employee(self._calendar(self.ZONE, with_lunch=False))
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": employee.id,
                "check_in": self._utc(self.ZONE, datetime(2026, 4, 4, 9, 0)),
            }
        )
        with patch.object(
            type(self.env["resource.calendar"]),
            "_attendance_intervals_batch",
            spy,
        ):
            attendance._scheduled_hours_on(local_day)
        self.assertTrue(seen, "the schedule must actually be asked about the day")
        start, stop = seen[0]
        return (
            stop.astimezone(pytz.UTC) - start.astimezone(pytz.UTC)
        ).total_seconds() / 3600

    def test_the_window_covers_a_twenty_five_hour_day(self):
        self.assertAlmostEqual(
            self._window_asked_for(self.LONG_DAY),
            25.0,
            3,
            "2026-04-04 in Santiago is 25 hours long; a window ending at "
            "`time.max` spans 24 of them and leaves the repeated hour out",
        )

    def test_the_window_covers_an_ordinary_day(self):
        self.assertAlmostEqual(
            self._window_asked_for(date(2026, 4, 6)),
            24.0,
            3,
            "the control: without it, a window that always overshot by an "
            "hour would satisfy the test above",
        )


@tagged("post_install", "-at_install")
class TestTheVersionIsChosenByTheLocalDay(ScheduleZoneCase):
    """Which version prices an attendance is circular: the local day needs the
    zone, and the zone comes from the version.

    Broken in favour of the UTC date it picked the wrong side of a schedule
    change, in both directions -- an evening attendance is already tomorrow for
    an employee far enough east, and an early-morning one is still yesterday for
    one far enough west.
    """

    def _moved(self, before_tz, after_tz, check_in, from_hour=7, to_hour=9):
        before = self._calendar(before_tz, with_lunch=False)
        before.attendance_ids.write({"hour_from": from_hour, "hour_to": from_hour + 8})
        after = self._calendar(after_tz, with_lunch=False)
        after.attendance_ids.write({"hour_from": to_hour, "hour_to": to_hour + 8})
        employee = self._employee(before)
        employee.create_version(
            {"date_version": date(2026, 9, 8), "resource_calendar_id": after.id}
        )
        self.env.flush_all()
        self.env.invalidate_all()
        return self.env["hr.attendance"].create(
            {
                "employee_id": employee.id,
                "check_in": check_in,
                "check_out": check_in + timedelta(hours=4),
            }
        )

    def test_an_evening_attendance_east_belongs_to_tomorrows_version(self):
        # 22:00 UTC on the 7th is 07:00 on the 8th in Tokyo.
        attendance = self._moved(
            "Asia/Tokyo", "Asia/Tokyo", datetime(2026, 9, 7, 22, 0)
        )
        self.assertEqual(attendance._local_check_in().date(), date(2026, 9, 8))
        self.assertEqual(
            attendance._schedule_version().date_version,
            date(2026, 9, 8),
            "the employee worked that day entirely under the new schedule; "
            "the UTC date said the 7th and priced it against the old one",
        )

    def test_an_early_attendance_west_belongs_to_yesterdays_version(self):
        # 02:00 UTC on the 8th is still 16:00 on the 7th in Honolulu.
        attendance = self._moved(
            "Pacific/Honolulu", "Pacific/Honolulu", datetime(2026, 9, 8, 2, 0)
        )
        self.assertEqual(attendance._local_check_in().date(), date(2026, 9, 7))
        self.assertEqual(
            attendance._schedule_version().date_version,
            date(2020, 1, 1),
            "the same error in the other direction: the UTC date said the 8th",
        )

    def test_the_version_chosen_agrees_with_the_day_that_chooses_it(self):
        for label, tz in (("east", "Asia/Tokyo"), ("west", "Pacific/Honolulu")):
            with self.subTest(side=label):
                check_in = (
                    datetime(2026, 9, 7, 22, 0)
                    if label == "east"
                    else datetime(2026, 9, 8, 2, 0)
                )
                attendance = self._moved(tz, tz, check_in)
                version = attendance._schedule_version()
                self.assertEqual(
                    attendance.employee_id.sudo()._get_version(
                        attendance._local_check_in().date()
                    ),
                    version,
                    "a fixed point: the version's own zone must agree with the "
                    "day that selects it",
                )

    def test_zones_that_straddle_the_change_in_opposite_directions_terminate(self):
        """No fixed point exists, so the resolution stops rather than loops."""
        attendance = self._moved(
            "Asia/Tokyo", "Pacific/Honolulu", datetime(2026, 9, 7, 22, 0)
        )
        self.assertTrue(
            attendance._schedule_version(),
            "there is no right answer here; there must still be an answer",
        )
        self.assertEqual(attendance.date, attendance._local_date_span()[0])
