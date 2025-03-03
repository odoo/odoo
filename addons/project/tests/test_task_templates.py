from odoo import Command

from odoo.addons.project.tests.test_project_base import TestProjectCommon


class TestTaskTemplates(TestProjectCommon):
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

    def test_copy_archived_template(self):
        """
        Copying a template should preserve its archived status
        """
        copied_template = self.template_task.copy()
        self.assertFalse(copied_template.active, "The copied template should also be archived")
