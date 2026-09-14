from datetime import date, datetime
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


class ScheduleZoneCase(TransactionCase):
    """Employees whose schedule is written in a zone their work contact is not.

    Every calendar in the rest of this suite is in UTC, which is the one
    configuration in which the module's three zone sources agree.
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
        return self.env["resource.calendar"].create(
            {
                "name": f"9-17 {tz}",
                "tz": tz,
                "company_id": self.company.id,
                "flexible_hours": False,
                "hours_per_day": 7 if with_lunch else 9,
                "attendance_ids": [Command.clear(), *_slots(with_lunch)],
            }
        )

    def _employee(self, calendar, personal_tz="Europe/Brussels", **extra):
        employee = self.env["hr.employee"].create(
            {
                "name": f"Works {calendar.tz}",
                "company_id": self.company.id,
                "resource_calendar_id": calendar.id,
                "date_version": date(2020, 1, 1),
                "contract_date_start": date(2020, 1, 1),
                **extra,
            }
        )
        # The resource's own zone follows the employee's work contact, not the
        # schedule. Setting it here is the whole point of these tests.
        employee.resource_id.tz = personal_tz
        return employee

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
        """`date` is resolved through the version in force on the day worked.

        Resolved through the employee's CURRENT schedule instead, moving an
        employee to another zone re-dates every day they have ever worked --
        away from the overtime lines of those days, which the engine files
        under the version's zone. And it does it silently: the stored value
        only moves the next time something retriggers the compute.
        """
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
