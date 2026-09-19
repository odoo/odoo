from datetime import date, datetime, timedelta

from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests.common import TransactionCase, tagged


# noon on a mid-month day: "six hours ago" is still today and still this month
@freeze_time("2025-06-17 12:00:00")
@tagged("post_install", "-at_install")
class TestTheHourTotalsFollowTheAttendances(TransactionCase):
    """`hours_today` and `hours_this_month` are not stored.

    A non-stored compute with no `@api.depends` is computed once and then held
    until something else happens to invalidate the cache, so an attendance
    created after the first read did not move it.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Freshness Ltd"})
        cls.company.resource_calendar_id = cls.env["resource.calendar"].create(
            {
                "name": "Round the clock",
                "company_id": cls.company.id,
                "tz": "UTC",
                "flexible_hours": False,
                "attendance_ids": [
                    Command.clear(),
                    *(
                        Command.create(
                            {
                                "name": f"day {day}",
                                "dayofweek": str(day),
                                "hour_from": 0,
                                "hour_to": 23.98,
                                "day_period": "morning",
                            }
                        )
                        for day in range(7)
                    ),
                ],
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Clocking", "company_id": cls.company.id, "tz": "UTC"}
        )
        cls.employee.resource_id.tz = "UTC"

    def _worked(self, hours_ago, hours):
        now = fields.Datetime.now()
        self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": now - timedelta(hours=hours_ago),
                "check_out": now - timedelta(hours=hours_ago - hours),
            }
        )
        self.env.flush_all()

    def test_hours_today_follows_a_later_attendance(self):
        self._worked(hours_ago=6, hours=2)
        self.assertAlmostEqual(self.employee.hours_today, 2.0, 3)
        self._worked(hours_ago=3, hours=3)
        self.assertAlmostEqual(
            self.employee.hours_today,
            5.0,
            3,
            "read once, then three more hours worked: without a declared "
            "dependency this still answered two",
        )

    def test_hours_this_month_follows_a_later_attendance(self):
        self._worked(hours_ago=6, hours=2)
        self.assertAlmostEqual(self.employee.hours_this_month, 2.0, 3)
        self._worked(hours_ago=3, hours=3)
        self.assertAlmostEqual(self.employee.hours_this_month, 5.0, 3)

    def test_the_totals_follow_a_deleted_attendance_too(self):
        self._worked(hours_ago=6, hours=2)
        second = self.env["hr.attendance"].search(
            [("employee_id", "=", self.employee.id)], limit=1
        )
        self.assertAlmostEqual(self.employee.hours_today, 2.0, 3)
        second.unlink()
        self.env.flush_all()
        self.assertAlmostEqual(self.employee.hours_today, 0.0, 3)


@tagged("post_install", "-at_install")
class TestExpectedHoursIgnoresAManagersCorrection(TransactionCase):
    """`expected_hours` is how many of the worked hours were not extra.

    It is measured against `duration`, what the rules computed, and not against
    `manual_duration`, which a manager edits. A correction is a statement about
    the overtime, never about what the schedule expected.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create(
            {"name": "Corrected Ltd", "attendance_overtime_validation": "no_validation"}
        )
        cls.calendar = cls.env["resource.calendar"].create(
            {
                "name": "Nine to five",
                "company_id": cls.company.id,
                "tz": "UTC",
                "flexible_hours": False,
                "attendance_ids": [
                    Command.clear(),
                    *(
                        Command.create(
                            {
                                "name": f"day {day}",
                                "dayofweek": str(day),
                                "hour_from": 9,
                                "hour_to": 17,
                                "day_period": "morning",
                            }
                        )
                        for day in range(7)
                    ),
                ],
            }
        )
        cls.ruleset = cls.env["hr.attendance.overtime.ruleset"].create(
            {
                "name": "Daily",
                "company_id": cls.company.id,
                "rule_ids": [
                    Command.create(
                        {
                            "name": "Beyond the day",
                            "base_off": "quantity",
                            "quantity_period": "day",
                            "expected_hours_from_contract": True,
                            "paid": True,
                            "amount_rate": 1.5,
                        }
                    )
                ],
            }
        )
        employee = cls.env["hr.employee"].create(
            {
                "name": "Twelve hours",
                "company_id": cls.company.id,
                "tz": "UTC",
                "resource_calendar_id": cls.calendar.id,
                "ruleset_id": cls.ruleset.id,
                "date_version": date(2020, 1, 1),
                "contract_date_start": date(2020, 1, 1),
            }
        )
        employee.resource_id.tz = "UTC"
        cls.attendance = cls.env["hr.attendance"].create(
            {
                "employee_id": employee.id,
                "check_in": datetime(2026, 9, 7, 9, 0),
                "check_out": datetime(2026, 9, 7, 21, 0),
            }
        )
        cls.line = cls.attendance.linked_overtime_ids

    def test_the_fixture_produced_overtime_to_correct(self):
        self.assertAlmostEqual(self.attendance.worked_hours, 12.0, 3)
        self.assertAlmostEqual(sum(self.line.mapped("duration")), 4.0, 3)
        self.assertAlmostEqual(
            self.attendance._scheduled_hours_on(date(2026, 9, 7)),
            8.0,
            3,
            "and the schedule really does hold eight, which is the number "
            "expected_hours must keep landing on",
        )

    def test_expected_hours_holds_through_a_correction(self):
        self.assertAlmostEqual(self.attendance.expected_hours, 8.0, 3)
        for corrected in (1.0, 0.0, 9.0):
            with self.subTest(manual_duration=corrected):
                self.line.manual_duration = corrected
                self.env.flush_all()
                self.attendance.invalidate_recordset()
                self.assertAlmostEqual(
                    self.attendance.expected_hours,
                    8.0,
                    3,
                    "the schedule did not change, so neither does this",
                )

    def test_the_correction_still_reaches_overtime_hours(self):
        self.line.manual_duration = 1.0
        self.env.flush_all()
        self.attendance.invalidate_recordset()
        self.assertAlmostEqual(
            self.attendance.overtime_hours,
            1.0,
            3,
            "the correction is a statement about the overtime and belongs here",
        )
