from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestProjectTemplatesTour(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        role_developer, role_designer = cls.env['project.role'].create([
            {'name': 'Developer'},
            {'name': 'Designer'},
        ])
        cls.project_template = cls.env["project.project"].create({
            "name": "Project Template",
            "is_template": True,
        })
        cls.task_inside_template = cls.env["project.task"].create([{
            "name": "Task in Project Template",
            "project_id": cls.project_template.id,
            'role_ids': [role_developer.id],
        }, {
            "name": "Task in Project Template1",
            "project_id": cls.project_template.id,
            'role_ids': [role_designer.id],
        }, {
            "name": "Task in Project Template2",
            "project_id": cls.project_template.id,
            'role_ids': [role_developer.id, role_designer.id],
        }])
        cls.user_developer, cls.user_designer = cls.env['res.users'].create([{
            'login': 'user_developer',
            'name': 'Developer User',
            'group_ids': [(6, 0, [cls.env.ref('project.group_project_user').id])],
        }, {
            'login': 'user_designer',
            'name': 'Designer User',
            'group_ids': [(6, 0, [cls.env.ref('project.group_project_user').id])],
        }])

    def test_project_templates_tour(self):
        user_admin = self.env.ref('base.user_admin')
        user_admin.write({
            'email': 'mitchell.admin@example.com',
        })
        self.start_tour("/odoo", "project_templates_tour", login="admin")

        new_project = self.env["project.project"].search([('name', '=', 'New Project')])
        tasks = new_project.task_ids
        self.assertEqual(
            tasks[0].user_ids,
            self.user_developer,
            "Task with only the Developer role should be assigned to the Developer User",
        )
        self.assertEqual(
            tasks[1].user_ids,
            self.user_designer,
            "Task with only the Designer role should be assigned to the Designer User",
        )
        self.assertEqual(
            tasks[2].user_ids,
            self.user_developer | self.user_designer,
            "Task with both roles should be assigned to both Developer and Designer Users",
        )
