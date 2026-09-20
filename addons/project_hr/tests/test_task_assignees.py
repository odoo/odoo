from odoo.fields import Command
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

    def test_a_user_without_an_employee_is_assigned_directly(self):
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
        self.assertEqual(task.direct_user_ids, stranger)
        self.assertEqual(task.user_ids, self.user | stranger)

    def test_a_user_without_an_employee_keeps_their_own_to_do(self):
        loner = new_test_user(
            self.env,
            login="assignee.loner",
            groups="base.group_user,project.group_project_user",
        )
        todo = (
            self.env["project.task"]
            .with_user(loner)
            .create({"name": "Own to-do", "user_ids": loner.ids})
        )
        self.assertEqual(todo.user_ids, loner)
        self.assertFalse(todo.employee_ids)

    def test_unlinking_and_clearing_reach_both_kinds_of_assignee(self):
        stranger = new_test_user(
            self.env, login="assignee.unlinked", groups="base.group_user"
        )
        task = self.env["project.task"].create(
            {
                "name": "Both kinds",
                "project_id": self.project.id,
                "user_ids": (self.user | stranger).ids,
            }
        )
        task.write({"user_ids": [Command.unlink(stranger.id)]})
        self.assertEqual(task.user_ids, self.user)
        task.write({"user_ids": [Command.clear()]})
        self.assertFalse(task.user_ids)
        self.assertFalse(task.employee_ids)

    def test_employees_written_alone_leave_direct_assignees_alone(self):
        stranger = new_test_user(
            self.env, login="assignee.kept", groups="base.group_user"
        )
        task = self.env["project.task"].create(
            {"name": "Kept", "project_id": self.project.id, "user_ids": stranger.ids}
        )
        task.employee_ids = self.employee
        self.assertEqual(task.user_ids, self.user | stranger)

    def test_an_empty_command_list_changes_nothing_and_false_clears(self):
        task = self.env["project.task"].create(
            {"name": "Kept", "project_id": self.project.id, "user_ids": self.user.ids}
        )

        task.write({"user_ids": []})
        self.assertEqual(task.user_ids, self.user, "an empty list is no command")

        task.write({"user_ids": False})
        self.assertFalse(task.user_ids)

    def test_a_falsy_id_in_a_bare_list_names_nobody(self):
        task = self.env["project.task"].create(
            {"name": "Nobody", "project_id": self.project.id}
        )

        task.write({"user_ids": [False]})

        self.assertFalse(task.user_ids)
        self.assertFalse(task.direct_user_ids)

    def test_the_callers_values_are_left_as_given(self):
        vals = {"user_ids": self.user.ids}
        first = self.env["project.task"].create(
            {"name": "First", "project_id": self.project.id, **vals}
        )
        second = self.env["project.task"].create(
            {"name": "Second", "project_id": self.project.id}
        )

        second.write(vals)
        self.assertEqual(vals, {"user_ids": self.user.ids})
        self.assertEqual((first | second).user_ids, self.user)

        shared = {"name": "Twins", "project_id": self.project.id, **vals}
        twins = self.env["project.task"].create([shared, shared])
        self.assertEqual(twins.mapped("user_ids"), self.user)
        self.assertEqual(shared["user_ids"], self.user.ids)
