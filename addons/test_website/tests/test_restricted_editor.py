# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo.tests.common import new_test_user
from odoo.tools import mute_logger


@odoo.tests.common.tagged('post_install', '-at_install')
class TestRestrictedEditor(odoo.tests.HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        website = cls.env['website'].search([], limit=1)
        fr = cls.env.ref('base.lang_fr').sudo()
        en = cls.env.ref('base.lang_en').sudo()

        fr.active = True

        website.default_lang_id = en
        website.language_ids = en + fr

        cls.env['website.menu'].create({
            'name': 'Model item',
            'url': '/test_website/model_item/1',
            'parent_id': website.menu_id.id,
            'sequence': 100,
        })

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_01_restricted_editor_only(self):
        self.restricted_editor = self.env['res.users'].create({
            'name': 'Restricted Editor',
            'login': 'restricted',
            'password': 'restricted',
            'groups_id': [(6, 0, [
                self.ref('base.group_user'),
                self.ref('website.group_website_restricted_editor'),
            ])]
        })
        self.start_tour(self.env['website'].get_client_action_url('/'), 'test_restricted_editor_only', login='restricted')

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_02_restricted_editor_test_admin(self):
        self.restricted_editor = self.env['res.users'].create({
            'name': 'Restricted Editor',
            'login': 'restricted',
            'password': 'restricted',
            'groups_id': [(6, 0, [
                self.ref('base.group_user'),
                self.ref('website.group_website_restricted_editor'),
                self.ref('test_website.group_test_website_admin'),
            ])]
        })
        self.start_tour(self.env['website'].get_client_action_url('/'), 'test_restricted_editor_test_admin', login='restricted')

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_03_restricted_editor_tester(self):
        """
        Tests that restricted users cannot edit ir.ui.view records despite being
        on a page of a record (main_object) they can edit.
        """
        self.user_test = new_test_user(self.env, login='restricted', website_id=False)
        self.user_test.groups_id |= self.env.ref('website.group_website_restricted_editor')
        self.user_test.groups_id |= self.env.ref('test_website.group_test_website_tester')
        self.start_tour(self.env['website'].get_client_action_url('/test_model/1'), 'test_restricted_editor_tester', login='restricted')
