from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestProjectManagerWrittenAsUser(TransactionCase):
    """A project manager need not be an employee.

    The manager is composed here from `employee_id.user_id`, because a project is
    usually run by someone on the payroll. It is not always: a consultant, a
    contractor or an administrator standing in manages projects without ever
    holding an employee record, and `direct_user_id` is where such a manager goes.
    Whichever field carries them, `user_id` names them and they follow the project.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.with_employee = new_test_user(
            cls.env, login="pm_with_employee", groups="project.group_project_manager"
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Managing Employee",
                "user_id": cls.with_employee.id,
                "company_id": cls.env.company.id,
            }
        )
        cls.without_employee = new_test_user(
            cls.env, login="pm_without_employee", groups="project.group_project_manager"
        )

    def _project(self, manager):
        return (
            self.env["project.project"]
            .with_context(mail_create_nolog=True)
            .create({"name": f"Project {manager.login}", "user_id": manager.id})
        )

    def test_a_manager_with_no_employee_is_still_the_manager(self):
        project = self._project(self.without_employee)

        self.assertEqual(project.user_id, self.without_employee)
        self.assertEqual(project.direct_user_id, self.without_employee)
        self.assertFalse(project.employee_id)

    def test_a_manager_with_an_employee_is_held_as_that_employee(self):
        project = self._project(self.with_employee)

        self.assertEqual(project.user_id, self.with_employee)
        self.assertEqual(project.employee_id, self.employee)
        self.assertFalse(project.direct_user_id)

    def test_a_manager_follows_their_project_either_way(self):
        for manager in (self.with_employee, self.without_employee):
            with self.subTest(manager=manager.login):
                project = self._project(manager)

                self.assertIn(
                    manager.partner_id,
                    project.message_partner_ids,
                    "the manager of a project follows it",
                )

    def test_reassigning_moves_the_manager_between_the_two_fields(self):
        project = self._project(self.without_employee)

        project.user_id = self.with_employee
        self.assertEqual(project.user_id, self.with_employee)
        self.assertEqual(project.employee_id, self.employee)
        self.assertFalse(project.direct_user_id)

        project.user_id = self.without_employee
        self.assertEqual(project.user_id, self.without_employee)
        self.assertEqual(project.direct_user_id, self.without_employee)
        self.assertFalse(project.employee_id)
