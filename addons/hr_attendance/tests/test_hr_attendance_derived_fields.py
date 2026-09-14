from datetime import date, datetime

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAttendanceFollowsItsOvertimeLines(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Derived Ltd"})
        cls.calendar = cls.env["resource.calendar"].create(
            {
                "name": "Eight a day",
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
                "name": "Daily",
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
                "name": "Derived",
                "company_id": cls.company.id,
                "resource_calendar_id": cls.calendar.id,
                "date_version": date(2020, 1, 1),
                "contract_date_start": date(2020, 1, 1),
                "ruleset_id": cls.ruleset.id,
            }
        )
        # Monday, ten hours worked against an eight-hour day: two hours over.
        cls.attendance = cls.env["hr.attendance"].create(
            {
                "employee_id": cls.employee.id,
                "check_in": datetime(2026, 8, 31, 8, 0),
                "check_out": datetime(2026, 8, 31, 18, 0),
            }
        )
        cls.line = cls.env["hr.attendance.overtime.line"].search(
            [("employee_id", "=", cls.employee.id)]
        )

    def _reread(self):
        self.env.flush_all()
        self.env.invalidate_all()
        return {
            "overtime_hours": self.attendance.overtime_hours,
            "validated_overtime_hours": self.attendance.validated_overtime_hours,
            "expected_hours": self.attendance.expected_hours,
        }

    def test_the_starting_point(self):
        self.assertEqual(len(self.line), 1)
        self.assertEqual(
            self._reread(),
            {
                "overtime_hours": 2.0,
                "validated_overtime_hours": 2.0,
                "expected_hours": 8.0,
            },
        )

    def test_correcting_the_encoded_hours_moves_the_extra_hours_only(self):
        """A correction to `manual_duration` is what a manager actually does.

        The attendance's `overtime_hours`, `validated_overtime_hours` and
        `expected_hours` are all derived from these lines, but declared
        `@api.depends` on `check_in`/`check_out`/`employee_id` instead -- their
        real trigger was hand-rolled in `hr.attendance.overtime.line.write`.
        Any field left out of that list kept its old value, and the attendance
        then reported two extra-hours figures that disagreed with each other.

        `expected_hours` is in the list and still recomputes; it just does not
        MOVE, because it is measured against `duration` -- what the rules
        computed -- and not against the column the manager edited. It read 5.0
        while it subtracted `manual_duration`, which let a correction restate
        how many hours the schedule had expected.
        """
        self.line.manual_duration = 5.0
        self.assertEqual(
            self._reread(),
            {
                "overtime_hours": 5.0,
                "validated_overtime_hours": 5.0,
                "expected_hours": 8.0,
            },
        )

    def test_refusing_the_overtime_leaves_it_counted_but_not_validated(self):
        self.line.action_refuse()
        values = self._reread()
        self.assertEqual(values["overtime_hours"], 2.0)
        self.assertEqual(values["validated_overtime_hours"], 0.0)
        self.assertEqual(self.attendance.overtime_status, "refused")

    def test_deleting_the_line_clears_the_derived_fields(self):
        self.line.unlink()
        self.assertEqual(
            self._reread(),
            {
                "overtime_hours": 0.0,
                "validated_overtime_hours": 0.0,
                "expected_hours": 10.0,
            },
        )
