from odoo.tests import HttpCase, tagged, new_test_user


@tagged("post_install", "-at_install")
class TestTimeOffOverviewMyDepartmentTour(HttpCase):

    def test_time_off_overview_my_department_tour(self):

        user_employee = new_test_user(self.env, login="employee", groups="base.group_user")
        self.start_tour("/", "time_off_overview_my_department_tour", login=user_employee.login)
