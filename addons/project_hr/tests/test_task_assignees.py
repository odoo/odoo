from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestTaskAssigneesWrittenAsUsers(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env,
            login="assignee.user",
            groups="base.group_user,project.group_project_user",
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Assignee", "user_id": cls.user.id}
        )
        cls.project = cls.env["project.project"].create({"name": "Assignees"})

    def test_a_personal_task_written_with_users_stays_visible_to_its_owner(self):
        task = (
            self.env["project.task"]
            .with_user(self.user)
            .create({"name": "Call supplier", "user_ids": self.user.ids})
        )
        self.assertEqual(task.employee_ids, self.employee)
        self.assertEqual(task.user_ids, self.user)

    def test_writing_users_assigns_their_employees_and_dates_the_assignment(self):
        task = self.env["project.task"].create(
            {"name": "Unassigned", "project_id": self.project.id}
        )
        self.assertFalse(task.date_assign)

        task.user_ids = self.user

        self.assertEqual(task.employee_ids, self.employee)
        self.assertTrue(task.date_assign)

    def test_employees_written_alongside_users_win(self):
        other = self.env["hr.employee"].create({"name": "Other assignee"})
        task = self.env["project.task"].create(
            {
                "name": "Both",
                "project_id": self.project.id,
                "user_ids": self.user.ids,
                "employee_ids": other.ids,
            }
        )
        self.assertEqual(task.employee_ids, other)

    def test_the_employee_of_the_task_company_is_chosen(self):
        other_company = self.env["res.company"].create({"name": "Assignee branch"})
        self.user.company_ids |= other_company
        branch_employee = self.env["hr.employee"].create(
            {
                "name": "Assignee at branch",
                "user_id": self.user.id,
                "company_id": other_company.id,
            }
        )
        project = self.env["project.project"].create(
            {"name": "Branch project", "company_id": other_company.id}
        )
        task = self.env["project.task"].create(
            {"name": "Branch task", "project_id": project.id, "user_ids": self.user.ids}
        )
        self.assertEqual(task.employee_ids, branch_employee)

    def test_a_user_without_an_employee_cannot_be_an_assignee(self):
        stranger = new_test_user(
            self.env, login="assignee.stranger", groups="base.group_user"
        )
        task = self.env["project.task"].create(
            {
                "name": "Stranger",
                "project_id": self.project.id,
                "user_ids": (self.user | stranger).ids,
            }
        )
        self.assertEqual(task.employee_ids, self.employee)
        self.assertEqual(task.user_ids, self.user)
