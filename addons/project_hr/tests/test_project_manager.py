from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestProjectManagerWrittenAsUser(TransactionCase):
    """A project manager is an employee (decided 2026-09-20).

    The manager is composed from `employee_id.user_id`. A `user_id` handed to
    create or write is routed to that user's employee, the project's company
    first, and a user who holds no employee record is refused rather than dropped.
    Whichever way they were named, the manager follows the project.
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
        cls.other_company = cls.env["res.company"].create({"name": "Elsewhere"})
        cls.elsewhere = new_test_user(
            cls.env,
            login="pm_elsewhere",
            groups="project.group_project_manager",
            company_ids=[(6, 0, (cls.env.company | cls.other_company).ids)],
        )
        cls.elsewhere_employee = cls.env["hr.employee"].create(
            {
                "name": "Managing Elsewhere",
                "user_id": cls.elsewhere.id,
                "company_id": cls.other_company.id,
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

    def test_a_manager_with_no_employee_is_refused(self):
        with self.assertRaises(UserError):
            self._project(self.without_employee)

        project = self._project(self.with_employee)
        with self.assertRaises(UserError):
            project.user_id = self.without_employee
        self.assertEqual(project.employee_id, self.employee)

    def test_a_manager_with_an_employee_is_held_as_that_employee(self):
        project = self._project(self.with_employee)

        self.assertEqual(project.user_id, self.with_employee)
        self.assertEqual(project.employee_id, self.employee)

    def test_a_manager_employed_in_another_company_is_held_through_that_employee(self):
        project = self._project(self.elsewhere)

        self.assertEqual(project.user_id, self.elsewhere)
        self.assertEqual(project.employee_id, self.elsewhere_employee)

    def test_a_manager_follows_their_project(self):
        project = self._project(self.with_employee)

        self.assertIn(
            self.with_employee.partner_id,
            project.message_partner_ids,
            "the manager of a project follows it",
        )

    def test_clearing_the_manager_clears_the_employee(self):
        project = self._project(self.with_employee)

        project.user_id = False
        self.assertFalse(project.employee_id)
        self.assertFalse(project.user_id)
