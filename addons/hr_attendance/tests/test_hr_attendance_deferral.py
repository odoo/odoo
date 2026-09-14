from datetime import date, datetime

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOvertimeDeferral(TransactionCase):
    """`_deferring_overtime` prices one period once instead of once per change.

    Its one constraint: inside the block the fields the regeneration produces
    hold whatever they held before it. A caller that reads them between two
    deferred operations reads stale values -- which is why the absence cron
    does not use it, and is the defect these tests exist to keep out.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create(
            {"name": "Deferral Ltd", "attendance_overtime_validation": "no_validation"}
        )
        cls.calendar = cls.env["resource.calendar"].create(
            {
                "name": "Eight a day",
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
                            "amount_rate": 1.0,
                        }
                    )
                ],
            }
        )

    def _employee(self, name):
        employee = self.env["hr.employee"].create(
            {
                "name": name,
                "company_id": self.company.id,
                "tz": "UTC",
                "resource_calendar_id": self.calendar.id,
                "ruleset_id": self.ruleset.id,
                "date_version": date(2020, 1, 1),
                "contract_date_start": date(2020, 1, 1),
            }
        )
        employee.resource_id.tz = "UTC"
        return employee

    def _open(self, employee):
        return self.env["hr.attendance"].create(
            {"employee_id": employee.id, "check_in": datetime(2026, 9, 7, 9, 0)}
        )

    def test_the_lines_are_the_same_as_without_the_block(self):
        immediate = self._open(self._employee("immediate"))
        immediate.write({"check_out": datetime(2026, 9, 7, 20, 0)})

        deferred = self._open(self._employee("deferred"))
        with deferred._deferring_overtime() as records:
            records.write({"check_out": datetime(2026, 9, 7, 20, 0)})

        def shape(attendance):
            return sorted(
                (line.date, round(line.duration, 6), line.status)
                for line in attendance.linked_overtime_ids
            )

        self.assertTrue(shape(immediate), "the fixture must produce overtime at all")
        self.assertEqual(shape(deferred), shape(immediate))
        self.assertEqual(deferred.overtime_hours, immediate.overtime_hours)

    def test_one_regeneration_for_a_whole_sweep(self):
        attendances = self.env["hr.attendance"]
        for index in range(4):
            attendances |= self._open(self._employee(f"swept {index}"))
        self.env.flush_all()

        regenerations = []
        update = type(attendances)._update_overtime

        def counting(records, windows=None):
            regenerations.append(len(records))
            return update(records, windows)

        self.patch(type(attendances), "_update_overtime", counting)
        with attendances._deferring_overtime() as records:
            for attendance in records:
                attendance.write({"check_out": datetime(2026, 9, 7, 20, 0)})
        self.assertEqual(
            len(regenerations),
            1,
            "four writes, one regeneration; without the block it is four",
        )

    def test_the_regenerated_fields_are_stale_inside_the_block(self):
        """The constraint, asserted rather than left in a docstring.

        `_cron_absence_detection` drops a marker whose `overtime_hours` came
        out zero. Run inside a deferral that read would be zero for every one
        of them and the cron would delete them all -- which it did, until a
        test caught it.
        """
        attendance = self._open(self._employee("stale"))
        with attendance._deferring_overtime() as records:
            records.write({"check_out": datetime(2026, 9, 7, 20, 0)})
            inside = records.overtime_hours
        self.assertEqual(
            inside,
            0.0,
            "inside the block the regeneration has not run, so this is the "
            "value from before it",
        )
        self.assertGreater(
            attendance.overtime_hours,
            0.0,
            "and once the block closes it is the real figure",
        )

    def test_a_nested_block_defers_to_the_outer_one(self):
        attendance = self._open(self._employee("nested"))
        with attendance._deferring_overtime() as outer:
            with outer._deferring_overtime() as inner:
                inner.write({"check_out": datetime(2026, 9, 7, 20, 0)})
            self.assertEqual(
                outer.overtime_hours,
                0.0,
                "the inner block must not flush; the outer one owns it",
            )
        self.assertGreater(attendance.overtime_hours, 0.0)

    def test_a_record_created_and_deleted_inside_the_block_is_not_priced(self):
        employee = self._employee("ephemeral")
        with employee.env["hr.attendance"]._deferring_overtime() as model:
            doomed = model.create(
                {
                    "employee_id": employee.id,
                    "check_in": datetime(2026, 9, 8, 9, 0),
                    "check_out": datetime(2026, 9, 8, 20, 0),
                }
            )
            doomed.unlink()
        self.assertFalse(
            self.env["hr.attendance.overtime.line"].search(
                [("employee_id", "=", employee.id), ("date", "=", date(2026, 9, 8))]
            ),
            "the flush must survive a record that no longer exists, and leave "
            "no line behind for the day it briefly occupied",
        )
