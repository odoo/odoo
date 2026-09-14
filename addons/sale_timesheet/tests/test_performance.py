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
        # 28 on a sale_timesheet-only database, 29 on a 153-module one: the
        # absolute count moves with the install, so these are the wider reading.
        # A narrower install logs `Query count less than expected` and passes.
        # The install-independent guard is
        # `test_making_a_project_billable_does_not_cost_a_query_per_task` below.
        with self.assertQueryCount(29):
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
        with self.assertQueryCount(30):
            project.write(
                {
                    "allow_billable": True,
                    "partner_id": self.partner_b.id,
                }
            )
        self.assertTrue(project.task_ids.sale_line_id)


@tagged("post_install", "-at_install")
class TestBillableProjectScaling(TestSaleTimesheet):
    def _cost_of_making_billable(self, task_count):
        project = self.env["project.project"].create(
            {
                "name": f"Scaling {task_count}",
                "task_ids": [
                    Command.create({"name": f"Task {index}"})
                    for index in range(task_count)
                ],
            }
        )
        self.env.flush_all()
        self.env.invalidate_all()
        before = self.env.cr.sql_statement_count
        project.write({"allow_billable": True, "partner_id": self.partner_b.id})
        self.env.flush_all()
        return self.env.cr.sql_statement_count - before

    def test_making_a_project_billable_does_not_cost_a_query_per_task(self):
        few = self._cost_of_making_billable(20)
        many = self._cost_of_making_billable(200)
        self.assertLessEqual(
            many,
            few + 5,
            f"200 tasks cost {many} statements against {few} for 20; making a "
            "project billable is querying per task again",
        )


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
