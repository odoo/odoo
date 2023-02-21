# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HOST, new_test_user, tagged
from odoo.tools import config, mute_logger

from odoo.addons.base.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestSystray(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_restricted_editor = cls.env.ref('website.group_website_restricted_editor')
        cls.group_tester = cls.env.ref('test_website.group_test_website_tester')
        # Do not rely on HttpCaseWithUserDemo to avoid having different user
        # definitions with and without demo data.
        cls.user_test = new_test_user(cls.env, login='testtest', website_id=False)
        other_website = cls.env['website'].create({
            'name': 'Other',
        })
        cls.env['ir.ui.view'].create({
            'name': "Patch to recognize other website",
            'website_id': other_website.id,
            'type': 'qweb',
            'inherit_id': cls.env.ref('test_website.test_model_page_layout').id,
            'arch': """
                <xpath expr="//span" position="after">
                    <div>Other</div>
                </xpath>
            """
        })
        # Remain on page when switching website
        cls.env['website'].search([]).homepage_url = '/test_model/1'

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_01_admin(self):
        self.start_tour(self.env['website'].get_client_action_url('/test_model/1'), 'test_systray_admin', login="admin")

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_02_reditor_tester(self):
        self.user_test.groups_id |= self.group_restricted_editor
        self.user_test.groups_id |= self.group_tester
        self.start_tour(self.env['website'].get_client_action_url('/test_model/1'), 'test_systray_reditor_tester', login="testtest")

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_03_reditor_not_tester(self):
        self.user_test.groups_id |= self.group_restricted_editor
        self.user_test.groups_id = self.user_test.groups_id.filtered(lambda group: group != self.group_tester)
        self.assertNotIn(self.group_tester.id, self.user_test.groups_id.ids, "User should not be a group_tester")
        self.start_tour(self.env['website'].get_client_action_url('/test_model/1'), 'test_systray_reditor_not_tester', login="testtest")

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_04_not_reditor_tester(self):
        self.user_test.groups_id = self.user_test.groups_id.filtered(lambda group: group != self.group_restricted_editor)
        self.user_test.groups_id |= self.group_tester
        self.assertNotIn(self.group_restricted_editor.id, self.user_test.groups_id.ids, "User should not be a group_restricted_editor")
        self.start_tour(self.env['website'].get_client_action_url('/test_model/1'), 'test_systray_not_reditor_tester', login="testtest")

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_05_not_reditor_not_tester(self):
        self.user_test.groups_id = self.user_test.groups_id.filtered(lambda group: group not in [self.group_restricted_editor, self.group_tester])
        self.assertNotIn(self.group_restricted_editor.id, self.user_test.groups_id.ids, "User should not be a group_restricted_editor")
        self.assertNotIn(self.group_tester.id, self.user_test.groups_id.ids, "User should not be a group_tester")
        self.start_tour(self.env['website'].get_client_action_url('/test_model/1'), 'test_systray_not_reditor_not_tester', login="testtest")
