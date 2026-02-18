from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tagged("post_install", "-at_install")
class TestTimeOffOverviewMyDepartmentTour(HttpCaseWithUserDemo):

    def test_time_off_overview_my_department_tour(self):
        self.user_demo.group_ids |= self.env.ref("hr_holidays.group_hr_holidays_employee")

        demo_employee = self.env["hr.employee"].create(
            {
                "name": "Demo Employee",
                "user_id": self.user_demo.id,
            },
        )

        leave_type = self.env["hr.work.entry.type"].create(
            {
                "name": "Test Leave Type",
                "code": "TEST_LEAVE",
                "requires_allocation": False,
            },
        )

        self.env["hr.leave"].create(
            {
                "name": "Test Leave",
                "employee_id": demo_employee.id,
                "work_entry_type_id": leave_type.id,
            },
        )

        self.start_tour("/odoo", "time_off_overview_my_department_tour", login=self.user_demo.login)
