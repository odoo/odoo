from datetime import datetime

from odoo.tests import tagged

from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet


@tagged("post_install", "-at_install")
class TestTimesheetAttendance(TestCommonTimesheet):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["hr.attendance"].create(
            {
                "employee_id": cls.empl_employee.id,
                "check_in": datetime(2022, 2, 9, 8, 0),
                "check_out": datetime(2022, 2, 9, 16, 0),
            }
        )

    def test_timesheet_attendance_report(self):
        self.env["account.analytic.line"].with_user(self.user_employee).create(
            {
                "name": "Test timesheet 1",
                "project_id": self.project_customer.id,
                "unit_amount": 6.0,
                "date": datetime(2022, 2, 9),
            }
        )
        total_timesheet, total_attendance = self.env[
            "hr.timesheet.attendance.report"
        ]._read_group(
            [
                ("employee_id", "=", self.empl_employee.id),
                ("date", ">=", datetime(2022, 2, 9, 8, 0)),
                ("date", "<=", datetime(2022, 2, 9, 16, 0)),
            ],
            aggregates=["total_timesheet:sum", "total_attendance:sum"],
        )[0]
        self.assertEqual(
            total_timesheet, 6.0, "Total timesheet in report should be 4.0"
        )
        self.assertEqual(
            total_attendance, 7.0, "Total attendance in report should be 8.0"
        )
        self.assertEqual(total_attendance - total_timesheet, 1)

    def _report_row(self, employee, date):
        return self.env["hr.timesheet.attendance.report"].search_read(
            [("employee_id", "=", employee.id), ("date", "=", date.date())],
            ["timesheets_cost", "attendance_cost", "cost_difference", "currency_id"],
        )

    def test_the_report_costs_a_timesheet_at_what_the_timesheet_recorded(self):
        self.empl_employee.hourly_cost = 10.0
        timesheet = self.env["account.analytic.line"].create(
            {
                "name": "Recorded cost",
                "project_id": self.project_customer.id,
                "employee_id": self.empl_employee.id,
                "unit_amount": 4.0,
                "date": datetime(2022, 2, 9),
            }
        )
        self.assertEqual(timesheet.amount, -40.0)

        timesheet.amount = -380.0
        self.env.flush_all()
        self.env.invalidate_all()
        [row] = self._report_row(self.empl_employee, datetime(2022, 2, 9))
        self.assertEqual(row["timesheets_cost"], 380.0)

    def test_a_later_raise_does_not_re_cost_past_timesheets(self):
        self.empl_employee.hourly_cost = 10.0
        self.env["account.analytic.line"].create(
            {
                "name": "Before the raise",
                "project_id": self.project_customer.id,
                "employee_id": self.empl_employee.id,
                "unit_amount": 4.0,
                "date": datetime(2022, 2, 9),
            }
        )
        self.env.flush_all()
        self.env.invalidate_all()
        [before] = self._report_row(self.empl_employee, datetime(2022, 2, 9))

        self.empl_employee.hourly_cost = 30.0
        self.env.flush_all()
        self.env.invalidate_all()
        [after] = self._report_row(self.empl_employee, datetime(2022, 2, 9))

        self.assertEqual(before["timesheets_cost"], 40.0)
        self.assertEqual(after["timesheets_cost"], 40.0)

    def test_the_cost_columns_carry_a_currency_and_still_add_up(self):
        report = self.env["hr.timesheet.attendance.report"]
        self.assertEqual(
            report._fields["timesheets_cost"].get_description(self.env)["type"],
            "monetary",
        )
        self.empl_employee.hourly_cost = 10.0
        self.env["account.analytic.line"].create(
            {
                "name": "Currency",
                "project_id": self.project_customer.id,
                "employee_id": self.empl_employee.id,
                "unit_amount": 4.0,
                "date": datetime(2022, 2, 9),
            }
        )
        self.env.flush_all()
        self.env.invalidate_all()
        [row] = self._report_row(self.empl_employee, datetime(2022, 2, 9))
        self.assertEqual(
            row["currency_id"][0], self.empl_employee.company_id.currency_id.id
        )
        self.assertEqual(
            row["cost_difference"],
            row["attendance_cost"] - row["timesheets_cost"],
        )
