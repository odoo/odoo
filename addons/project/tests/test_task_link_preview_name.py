import odoo.tests
from odoo.tests.common import HttpCase, new_test_user
from odoo.tools.json import scriptsafe as json_safe


@odoo.tests.tagged('post_install', '-at_install')
class TestTaskLinkPreviewName(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        admin_user = new_test_user(cls.env, login='admin_user', groups='base.group_user,base.group_system')
        cls.admin = admin_user.login

        cls.project_internal_link_display = cls.env['project.project'].create({
            'name': 'project',
            'display_name': 'project_display_name',
            'description': 'project_description',
        })
        cls.task_internal_link_customized = cls.env['project.task'].create({
            'name': 'task1',
            'display_name': 'task1_display_name',
            'link_preview_name': 'test1 | test parent',
            'project_id': cls.project_internal_link_display.id,
            'description': 'task1_description',
        })

    def test_01_task_link_preview_name(self):
        self.authenticate(self.admin, self.admin)
        # retrieve metadata of an record with customerized link_preview_name
        response_with_preview_name = self.url_open(
            '/html_editor/link_preview_internal',
            data=json_safe.dumps({
                "params": {
                    "preview_url": f"/odoo/all-tasks/{self.task_internal_link_customized.id}",
                }
            }),
            headers={"Content-Type": "application/json"}
        )
        self.assertEqual(200, response_with_preview_name.status_code)
        self.assertTrue('link_preview_name' in response_with_preview_name.text)
