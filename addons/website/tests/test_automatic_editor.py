from unittest.mock import patch

from odoo.tests import HttpCase, tagged

@tagged('post_install', '-at_install')
class TestAutomaticEditor(HttpCase):

    def _theme_upgrade_upstream(self):
        # Because we cannot do _theme_upgrade_upstream, the theme install action
        # isn't consumed, so it puts the user back on the install theme screen.
        # So actions prior are disabled and an action that will trigger what
        # needs to be tested is created.
        actions = self.env['ir.actions.todo'].search([('state', '=', 'open')])
        actions.write({'state': 'done'})
        self.env['ir.actions.todo'].create({'action_id': self.env.ref('website.action_website_edit').id, 'state': 'open'})

    def setUp(self):
        super().setUp()
        patcher = patch('odoo.addons.website.models.ir_module_module.IrModuleModule._theme_upgrade_upstream', wraps=self._theme_upgrade_upstream)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_01_automatic_editor_on_new_website(self):
        # We create a lang because if the new website is displayed in this lang
        # instead of the website's default one, the editor won't automatically
        # start.
        self.env['res.lang'].create({
            'name': 'Parseltongue',
            'code': 'pa_GB',
            'iso_code': 'pa_GB',
            'url_code': 'pa_GB',
        })
        self.start_tour('/', 'automatic_editor_on_new_website', login='admin')
