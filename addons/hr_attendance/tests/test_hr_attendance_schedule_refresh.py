from datetime import datetime

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "hr_attendance_schedule_refresh")
class TestTheStoredFieldsFollowTheSchedule(TransactionCase):
    """`worked_hours` and `date` are stored and computed from the schedule.

    Neither can declare that dependency -- the schedule is resolved as a fixed
    point over the employee's versions, not by a field path -- so editing a
    calendar used to leave both fields on a value nothing would ever refresh.
    Worse than stale: the next unrelated write to one attendance retriggered
    the compute, so two identical days could end up stored differently.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env["resource.calendar"].create(
            {
                "name": "08-17 with an hour of lunch",
                "tz": "UTC",
                "flexible_hours": False,
                "attendance_ids": [
                    Command.clear(),
                    *(
                        command
                        for day in range(5)
                        for command in (
                            Command.create(
                                {
                                    "name": f"morning {day}",
                                    "dayofweek": str(day),
                                    "hour_from": 8,
                                    "hour_to": 12,
                                    "day_period": "morning",
                                }
                            ),
                            Command.create(
                                {
                                    "name": f"lunch {day}",
                                    "dayofweek": str(day),
                                    "hour_from": 12,
                                    "hour_to": 13,
                                    "day_period": "lunch",
                                }
                            ),
                            Command.create(
                                {
                                    "name": f"afternoon {day}",
                                    "dayofweek": str(day),
                                    "hour_from": 13,
                                    "hour_to": 17,
                                    "day_period": "afternoon",
                                }
                            ),
                        )
                    ),
                ],
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Priced by the schedule",
                "resource_calendar_id": cls.calendar.id,
                "tz": "UTC",
            }
        )
        cls.employee.resource_id.tz = "UTC"

    def _worked(self, day, hour_from=8, hour_to=17):
        return self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2026, 9, day, hour_from, 0),
                "check_out": datetime(2026, 9, day, hour_to, 0),
            }
        )

    def _drop_the_lunch(self):
        self.calendar.attendance_ids.filtered(
            lambda line: line.day_period == "lunch"
        ).unlink()
        self.env.flush_all()

    def test_removing_the_lunch_refreshes_worked_hours(self):
        monday = self._worked(7)
        tuesday = self._worked(8)
        self.env.flush_all()
        self.assertEqual(monday.worked_hours, 8.0)
        self.assertEqual(tuesday.worked_hours, 8.0)

        self._drop_the_lunch()
        self.env.invalidate_all()

        self.assertEqual(
            monday.worked_hours,
            9.0,
            "the schedule stopped deducting lunch, so the day it was deducted "
            "from has to be re-priced",
        )
        self.assertEqual(tuesday.worked_hours, 9.0)

    def test_two_identical_days_stay_identical(self):
        monday = self._worked(7)
        tuesday = self._worked(8)
        self.env.flush_all()
        self._drop_the_lunch()

        # An unrelated write to one of the two. It used to be the only thing
        # that re-priced a day, which is how two identical days ended up
        # stored eight and nine.
        monday.write({"check_out": datetime(2026, 9, 7, 17, 1)})
        monday.write({"check_out": datetime(2026, 9, 7, 17, 0)})
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(
            monday.worked_hours,
            tuesday.worked_hours,
            "same employee, same schedule, same hours: touching one of the two "
            "must not be what decides its value",
        )

    def test_changing_the_zone_refreshes_the_day(self):
        late = self._worked(7, hour_from=22, hour_to=23)
        self.env.flush_all()
        self.assertEqual(str(late.date), "2026-09-07")

        self.calendar.tz = "Asia/Tokyo"
        self.employee.resource_id.tz = "Asia/Tokyo"
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(
            str(late.date),
            "2026-09-08",
            "22:00 UTC is the next day in Tokyo, and the attendance is filed "
            "under the day its schedule places it on",
        )
