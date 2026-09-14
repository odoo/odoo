from odoo.tests import Form, new_test_user, tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestProjectProject(TransactionCase):
    def test_projects_to_make_billable(self):
        Project = self.env["project.project"]
        Task = self.env["project.task"]
        partner = self.env["res.partner"].create({"name": "Mur en béton"})
        project1, project2, project3 = Project.create(
            [
                {
                    "name": "Project with partner",
                    "partner_id": partner.id,
                    "allow_billable": False,
                },
                {"name": "Project without partner", "allow_billable": False},
                {"name": "Project without partner 2", "allow_billable": False},
            ]
        )
        Task.create(
            [
                {
                    "name": "Task with partner in project 2",
                    "project_id": project2.id,
                    "partner_id": partner.id,
                },
                {
                    "name": "Task without partner in project 2",
                    "project_id": project2.id,
                },
                {
                    "name": "Task without partner in project 3",
                    "project_id": project3.id,
                },
            ]
        )
        projects_to_make_billable = Project.search(
            Project._get_domain_projects_to_make_billable()
        )
        (non_billable_projects,) = Task._read_group(
            Task._get_domain_projects_to_make_billable(
                [("project_id", "not in", projects_to_make_billable.ids)]
            ),
            [],
            ["project_id:recordset"],
        )[0]
        projects_to_make_billable += non_billable_projects
        self.assertEqual(projects_to_make_billable, project1 + project2)

    def test_a_manager_without_sales_rights_opens_a_new_project_form(self):
        user = new_test_user(
            self.env,
            login="project_only",
            groups="base.group_user,project.group_project_manager",
        )
        self.assertFalse(user.has_group("sale.group_sale_salesman"))
        form = Form(self.env["project.project"].with_user(user))
        form.name = "Created without sales rights"
        project = form.save()
        self.assertEqual(project.name, "Created without sales rights")
