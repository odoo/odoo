# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tagged('post_install', '-at_install')
class TestSystray(HttpCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_restricted_editor = cls.env.ref('website.group_website_restricted_editor')
        cls.group_tester = cls.env.ref('test_website.group_test_website_tester')
        # Remain on page when switching website
        cls.env['website'].search([]).homepage_url = '/test_model/1'

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_01_admin(self):
        self.start_tour(self.env['website'].get_client_action_url('/test_model/1'), 'test_systray_admin', login="admin")

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_02_reditor_tester(self):
        self.user_demo.groups_id |= self.group_restricted_editor
        self.user_demo.groups_id |= self.group_tester
        self.start_tour(self.env['website'].get_client_action_url('/test_model/1'), 'test_systray_reditor_tester', login="demo")

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_03_reditor_not_tester(self):
        self.user_demo.groups_id |= self.group_restricted_editor
        self.user_demo.groups_id = self.user_demo.groups_id.filtered(lambda group: group != self.group_tester)
        self.start_tour(self.env['website'].get_client_action_url('/test_model/1'), 'test_systray_reditor_not_tester', login="demo")

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_04_not_reditor_tester(self):
        self.user_demo.groups_id = self.user_demo.groups_id.filtered(lambda group: group != self.group_restricted_editor)
        self.user_demo.groups_id |= self.group_tester
        self.start_tour(self.env['website'].get_client_action_url('/test_model/1'), 'test_systray_not_reditor_tester', login="demo")

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_05_not_reditor_not_tester(self):
        self.user_demo.groups_id = self.user_demo.groups_id.filtered(lambda group: group not in [self.group_restricted_editor, self.group_tester])
        self.start_tour(self.env['website'].get_client_action_url('/test_model/1'), 'test_systray_not_reditor_not_tester', login="demo")
