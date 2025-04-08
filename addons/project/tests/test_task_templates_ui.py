from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestTaskTemplatesTour(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_with_templates = cls.env["project.project"].create({
            "name": "Project with Task Template",
            "type_ids": [Command.link(cls.env.ref("project.project_project_stage_0").id)],
        })
        cls.template_task = cls.env["project.task"].create({
            "name": "Template",
            "project_id": cls.project_with_templates.id,
            "active": False,
            "is_template": True,
            "description": "Template description",
            "stage_id": cls.env.ref("project.project_project_stage_0").id,
        })

    def test_task_templates_tour(self):
        self.start_tour("/odoo", "project_task_templates_tour", login="admin")
