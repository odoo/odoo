from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale_timesheet.tests.test_sale_timesheet import TestSaleTimesheet


@tagged("post_install", "-at_install")
class TestPerformanceTimesheet(TestSaleTimesheet):
    def test_performance_billable_project_change_customer(self):
        project = self.env["project.project"].create(
            {
                "name": "Perf Project",
                "task_ids": [Command.create({"name": f"Task {i}"}) for i in range(50)],
            }
        )
        self.assertFalse(project.task_ids.sale_line_id)
        self.env.invalidate_all()
        with self.assertQueryCount(87):
            project.write(
                {
                    "allow_billable": True,
                    "partner_id": self.partner_b.id,
                }
            )
        self.assertTrue(project.task_ids.sale_line_id)

        project.allow_billable = False
        self.assertFalse(project.task_ids.sale_line_id)
        self.env["project.task"].create(
            [
                {
                    "name": f"Task {i}",
                    "project_id": project.id,
                }
                for i in range(50, 100)
            ]
        )
        self.env.invalidate_all()
        with self.assertQueryCount(130):
            project.write(
                {
                    "allow_billable": True,
                    "partner_id": self.partner_b.id,
                }
            )
        self.assertTrue(project.task_ids.sale_line_id)


@tagged("post_install", "-at_install")
class TestEmployeeMappingLookup(TestSaleTimesheet):
    def _employee_rate_project_with_timesheets(self, count):
        employees = self.env["hr.employee"].create(
            [{"name": f"Mapped {i}", "hourly_cost": 10.0 + i} for i in range(count)]
        )
        project = self.env["project.project"].create(
            {
                "name": "Employee Rate Project",
                "allow_timesheets": True,
                "allow_billable": True,
                "partner_id": self.partner_b.id,
                "sale_line_employee_ids": [
                    Command.create({"employee_id": employee.id})
                    for employee in employees
                ],
            }
        )
        self.assertEqual(project.pricing_type, "employee_rate")
        return self.env["account.analytic.line"].create(
            [
                {
                    "name": f"Timesheet {i}",
                    "project_id": project.id,
                    "employee_id": employee.id,
                    "unit_amount": 1.0,
                }
                for i, employee in enumerate(employees)
            ]
        )

    def test_the_hourly_cost_of_many_timesheets_costs_no_query_per_timesheet(self):
        timesheets = self._employee_rate_project_with_timesheets(20)
        self.env.invalidate_all()
        timesheets[0]._hourly_cost()
        with self.assertQueryCount(0):
            costs = [timesheet._hourly_cost() for timesheet in timesheets]
        self.assertEqual(costs, [10.0 + i for i in range(20)])
