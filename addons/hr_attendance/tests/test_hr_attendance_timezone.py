from datetime import date, datetime

from freezegun import freeze_time

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOvertimeDayAttribution(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Far East Ltd"})
        cls.calendar = cls.env["resource.calendar"].create(
            {
                "name": "Auckland 8h",
                "company_id": cls.company.id,
                "tz": "Pacific/Auckland",
                "attendance_ids": [
                    Command.clear(),
                    *(
                        Command.create(
                            {
                                "name": day,
                                "dayofweek": str(index),
                                "hour_from": 8,
                                "hour_to": 16,
                                "day_period": "morning",
                            }
                        )
                        for index, day in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"])
                    ),
                ],
            }
        )
        cls.ruleset = cls.env["hr.attendance.overtime.ruleset"].create(
            {
                "name": "Beyond the scheduled day",
                "company_id": cls.company.id,
                "rule_ids": [
                    Command.create(
                        {
                            "name": "Daily",
                            "base_off": "quantity",
                            "quantity_period": "day",
                            "expected_hours_from_contract": True,
                            "paid": True,
                            "amount_rate": 1.0,
                        }
                    )
                ],
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Twelve Hours Ahead",
                "company_id": cls.company.id,
                "resource_calendar_id": cls.calendar.id,
                "date_version": date(2020, 1, 1),
                "contract_date_start": date(2020, 1, 1),
                "ruleset_id": cls.ruleset.id,
            }
        )
        cls.attendance = cls.env["hr.attendance"].create(
            {
                "employee_id": cls.employee.id,
                "check_in": datetime(2026, 8, 30, 20, 0),
                "check_out": datetime(2026, 8, 31, 8, 0),
            }
        )
        cls.lines = cls.env["hr.attendance.overtime.line"].search(
            [("employee_id", "=", cls.employee.id)]
        )

    def test_the_attendance_falls_on_the_local_day(self):
        self.assertEqual(self.attendance.date, date(2026, 8, 31))

    def test_overtime_is_dated_the_same_local_day_as_its_attendance(self):
        self.assertTrue(self.lines, "the twelve-hour day must produce overtime")
        self.assertEqual(
            set(self.lines.mapped("date")),
            {date(2026, 8, 31)},
            "the overtime line belongs to the local day the employee worked, "
            "the same day its attendance is stored under. Intervals reaching "
            "the day attribution are ALREADY in the employee's local time; "
            "converting them again -- `.astimezone(tz)` on a naive datetime "
            "reads it as the server's time zone -- pushes the day forward for "
            "any employee far enough east, and dates their overtime tomorrow.",
        )

    def test_the_overtime_amount_is_unaffected_by_the_day_attribution(self):
        self.assertAlmostEqual(sum(self.lines.mapped("duration")), 4.0, 2)

    def test_the_kiosk_reads_todays_overtime_in_the_employees_time_zone(self):
        from odoo.addons.hr_attendance.controllers.main import HrAttendance

        with freeze_time("2026-08-31 20:00:00"):
            self.env["hr.attendance.overtime.line"].create(
                {
                    "employee_id": self.employee.id,
                    "date": date(2026, 9, 1),
                    "duration": 2.5,
                    "time_start": datetime(2026, 8, 31, 20, 0),
                    "time_stop": datetime(2026, 8, 31, 22, 30),
                }
            )
            self.assertAlmostEqual(
                HrAttendance._get_overtime_today(self.employee),
                2.5,
                2,
                "the employee's 'today' is 2026-09-01; the server's is "
                "2026-08-31, and so is the requesting user's",
            )


@tagged("post_install", "-at_install")
class TestWorkZoneBeatsCalendarZone(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Split Zones Ltd"})
        cls.calendar = cls.env["resource.calendar"].create(
            {
                "name": "Office 8h",
                "company_id": cls.company.id,
                "tz": "UTC",
                "attendance_ids": [
                    Command.clear(),
                    *(
                        Command.create(
                            {
                                "name": day,
                                "dayofweek": str(index),
                                "hour_from": 8,
                                "hour_to": 16,
                                "day_period": "morning",
                            }
                        )
                        for index, day in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"])
                    ),
                ],
            }
        )
        cls.ruleset = cls.env["hr.attendance.overtime.ruleset"].create(
            {
                "name": "Beyond the scheduled day",
                "company_id": cls.company.id,
                "rule_ids": [
                    Command.create(
                        {
                            "name": "Daily",
                            "base_off": "quantity",
                            "quantity_period": "day",
                            "expected_hours_from_contract": True,
                            "paid": True,
                            "amount_rate": 1.0,
                        }
                    )
                ],
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Deployed to Auckland",
                "company_id": cls.company.id,
                "tz": "Pacific/Auckland",
                "resource_calendar_id": cls.calendar.id,
                "date_version": date(2020, 1, 1),
                "contract_date_start": date(2020, 1, 1),
                "ruleset_id": cls.ruleset.id,
            }
        )
        cls.attendance = cls.env["hr.attendance"].create(
            {
                "employee_id": cls.employee.id,
                "check_in": datetime(2026, 8, 30, 20, 0),
                "check_out": datetime(2026, 8, 31, 8, 0),
            }
        )
        cls.lines = cls.env["hr.attendance.overtime.line"].search(
            [("employee_id", "=", cls.employee.id)]
        )

    def test_the_two_zones_really_differ(self):
        self.assertEqual(self.employee.tz, "Pacific/Auckland")
        self.assertEqual(self.employee.resource_calendar_id.tz, "UTC")

    def test_the_attendance_falls_on_the_scheduled_day(self):
        self.assertEqual(self.attendance.date, date(2026, 8, 31))

    def test_overtime_is_dated_the_same_day_as_its_attendance(self):
        self.assertTrue(self.lines, "the twelve-hour day must produce overtime")
        self.assertEqual(
            set(self.lines.mapped("date")),
            {self.attendance.date},
            "`hr.attendance.date` resolves the day in the employee's work zone "
            "and the overtime engine must resolve it the same way; reading the "
            "calendar's zone splits one shift across two dates as soon as the "
            "employee works away from the office: the attendance lands on "
            "2026-08-31 and its overtime on 2026-08-30.",
        )

    def test_the_overtime_amount_is_measured_against_the_scheduled_day(self):
        self.assertAlmostEqual(sum(self.lines.mapped("duration")), 4.0, 2)
