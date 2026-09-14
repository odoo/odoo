from datetime import date, datetime

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestATimingWindowThatWrapsMidnight(TransactionCase):
    """A night premium is `timing_start` 22:00, `timing_stop` 06:00 -- a window
    whose end is before its start.

    `get_day_rule_intervals` cannot build that directly, so it builds the
    complement, [06:00, 22:00], and inverts it inside the day. Nothing covered
    that branch: no test in the suite set `timing_start > timing_stop`, so the
    inversion could have been deleted and every one of them stayed green.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create(
            {
                "name": "Night Shift Ltd",
                "attendance_overtime_validation": "no_validation",
            }
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
                "name": "Night premium",
                "company_id": cls.company.id,
                "rule_ids": [
                    Command.create(
                        {
                            "name": "22:00 to 06:00",
                            "base_off": "timing",
                            "timing_type": "work_days",
                            "timing_start": 22.0,
                            "timing_stop": 6.0,
                            "paid": True,
                            "amount_rate": 2.0,
                        }
                    )
                ],
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Night worker",
                "company_id": cls.company.id,
                "tz": "UTC",
                "resource_calendar_id": cls.calendar.id,
                "ruleset_id": cls.ruleset.id,
                "date_version": date(2020, 1, 1),
                "contract_date_start": date(2020, 1, 1),
            }
        )
        cls.employee.resource_id.tz = "UTC"

    def _night_hours(self, check_in, check_out):
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": check_in,
                "check_out": check_out,
            }
        )
        return attendance, sum(attendance.linked_overtime_ids.mapped("duration"))

    def test_the_rule_really_wraps(self):
        rule = self.ruleset.rule_ids
        self.assertGreater(
            rule.timing_start,
            rule.timing_stop,
            "the fixture must describe a window whose end is before its start, "
            "or none of the assertions below reach the inversion",
        )

    def test_a_shift_across_midnight_is_paid_for_the_night_part_only(self):
        attendance, hours = self._night_hours(
            datetime(2026, 9, 7, 20, 0), datetime(2026, 9, 8, 8, 0)
        )
        self.assertAlmostEqual(
            hours,
            8.0,
            2,
            "twelve hours worked, of which 22:00-06:00 is inside the window",
        )
        self.assertEqual(
            sorted(attendance.linked_overtime_ids.mapped("duration")),
            [2.0, 6.0],
            "and it is split across the two days it falls on: two hours before "
            "midnight, six after",
        )
        self.assertEqual(
            sorted(attendance.linked_overtime_ids.mapped("date")),
            [date(2026, 9, 7), date(2026, 9, 8)],
        )

    def test_a_shift_wholly_inside_the_window_is_paid_in_full(self):
        _attendance, hours = self._night_hours(
            datetime(2026, 9, 14, 23, 0), datetime(2026, 9, 15, 2, 0)
        )
        self.assertAlmostEqual(hours, 3.0, 2)

    def test_a_day_shift_earns_nothing(self):
        _attendance, hours = self._night_hours(
            datetime(2026, 9, 21, 9, 0), datetime(2026, 9, 21, 17, 0)
        )
        self.assertAlmostEqual(
            hours,
            0.0,
            2,
            "the control: without it, a rule that matched the whole day would "
            "satisfy every assertion above",
        )

    def test_the_night_rate_reaches_the_line(self):
        attendance, _hours = self._night_hours(
            datetime(2026, 9, 28, 23, 0), datetime(2026, 9, 29, 1, 0)
        )
        self.assertEqual(
            set(attendance.linked_overtime_ids.mapped("amount_rate")),
            {2.0},
            "a premium window exists to be paid at its rate",
        )
