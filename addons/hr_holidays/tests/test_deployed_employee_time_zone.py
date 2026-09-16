from datetime import UTC, date, datetime

from odoo.tests.common import TransactionCase


class TestDeployedEmployeeTimeZone(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.office_calendar = cls.env["resource.calendar"].create(
            {"name": "Corporate office", "tz": "America/Mexico_City"}
        )
        cls.deployed = cls.env["hr.employee"].create(
            {
                "name": "Deployed in Mazatlan",
                "tz": "America/Mazatlan",
                "resource_calendar_id": cls.office_calendar.id,
                "date_version": date(2030, 1, 1),
                "contract_date_start": date(2030, 1, 1),
            }
        )
        cls.hourly = cls.env["hr.leave.type"].create(
            {
                "name": "Hours off",
                "requires_allocation": False,
                "request_unit": "hour",
                "leave_validation_type": "no_validation",
            }
        )

    def test_an_employee_works_the_office_schedule_in_their_own_time_zone(self):
        self.assertEqual(self.deployed._get_schedule_tz(), "America/Mazatlan")
        self.assertEqual(
            self.deployed.version_id._get_schedule_tz(), "America/Mazatlan"
        )

        start = datetime(2030, 3, 4, tzinfo=UTC)
        stop = datetime(2030, 3, 5, tzinfo=UTC)
        first_interval = next(
            iter(
                self.deployed.resource_id._get_valid_work_intervals(start, stop)[0][
                    self.deployed.resource_id.id
                ]
            )
        )
        self.assertEqual(
            first_interval[0].astimezone(UTC), datetime(2030, 3, 4, 15, 0, tzinfo=UTC)
        )

    def test_hours_off_are_requested_in_the_employee_time_zone(self):
        leave = self.env["hr.leave"].create(
            {
                "name": "Two hours",
                "employee_id": self.deployed.id,
                "holiday_status_id": self.hourly.id,
                "request_date_from": date(2030, 3, 4),
                "request_date_to": date(2030, 3, 4),
                "request_hour_from": 9.0,
                "request_hour_to": 11.0,
            }
        )
        self.assertEqual(leave.tz, "America/Mazatlan")
        self.assertEqual(leave.date_from, datetime(2030, 3, 4, 16, 0))
        self.assertEqual(leave.date_to, datetime(2030, 3, 4, 18, 0))


class TestLeaveKeepsItsScheduleException(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Reconciled"})
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Days off",
                "requires_allocation": False,
                "leave_validation_type": "no_validation",
            }
        )

    def _exception_of(self, leave):
        return self.env["resource.schedule.exception"].search(
            [("holiday_id", "=", leave.id)]
        )

    def test_reapplying_a_leave_rewrites_its_row_instead_of_replacing_it(self):
        leave = (
            self.env["hr.leave"]
            .sudo()
            .create(
                {
                    "name": "A week",
                    "employee_id": self.employee.id,
                    "holiday_status_id": self.leave_type.id,
                    "request_date_from": date(2030, 4, 1),
                    "request_date_to": date(2030, 4, 2),
                }
            )
        )
        exception = self._exception_of(leave)
        self.assertEqual(len(exception), 1)

        leave._apply_leave_request()
        self.assertEqual(
            self._exception_of(leave),
            exception,
            "re-applying an approved leave keeps the row it already has",
        )

        self.employee.name = "Reconciled Renamed"
        leave._apply_leave_request()
        rewritten = self._exception_of(leave)
        self.assertEqual(
            rewritten, exception, "a changed leave rewrites its row in place"
        )
        self.assertEqual(rewritten.name, "Reconciled Renamed: Time Off")

        leave.action_refuse()
        self.assertFalse(self._exception_of(leave))
