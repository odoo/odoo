# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

import odoo.tests

from odoo.addons.website.tools import MockRequest
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


@odoo.tests.common.tagged('post_install', '-at_install')
class TestRestrictedEditorBranding(odoo.tests.TransactionCase):
    """
    A restricted editor may be granted the write access on a subset of the
    views. Only that subset may receive the branding, otherwise saving the page
    ends up on an access rights error.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref('website.default_website')
        # A record the restricted editor may write, so that the page itself is
        # considered editable.
        cls.main_object = cls.env.ref('test_website.test_model_generic')

        cls.writable_view, cls.forbidden_view = cls.env['ir.ui.view'].create([{
            'name': 'Writable Block',
            'type': 'qweb',
            'key': 'test_website.branding_writable',
            'arch': '<div id="writable">writable</div>',
        }, {
            'name': 'Forbidden Block',
            'type': 'qweb',
            'key': 'test_website.branding_forbidden',
            'arch': '<div id="forbidden">forbidden</div>',
        }])
        cls.page_view = cls.env['ir.ui.view'].create({
            'name': 'Branding Page',
            'type': 'qweb',
            'key': 'test_website.branding_page',
            'arch': """<div id="page">
                <t t-call="test_website.branding_writable"/>
                <t t-call="test_website.branding_forbidden"/>
            </div>""",
        })

        # Let the restricted editors write the views, and narrow that down
        # to a subset with a record rule.
        restricted_group = cls.env.ref('website.group_website_restricted_editor')
        cls.env.ref('website.access_website_ir_ui_view_restricted_editor').perm_write = True
        cls.env['ir.rule'].create({
            'name': 'restricted editor: write some views',
            'model_id': cls.env['ir.model']._get_id('ir.ui.view'),
            'groups': [(6, 0, restricted_group.ids)],
            'domain_force': "[('key', '=', 'test_website.branding_writable')]",
            'perm_read': False,
            'perm_write': True,
            'perm_create': False,
            'perm_unlink': False,
        })

        cls.restricted_editor = new_test_user(cls.env, login='restricted_branding', website_id=False)
        cls.restricted_editor.groups_id |= restricted_group
        cls.restricted_editor.groups_id |= cls.env.ref('test_website.group_test_website_tester')

    def _branded_view_ids(self, user):
        """
        Render the page as ``user`` and collect the branded views.

        :param user: the user the page is rendered for
        :return: the ids of the views that received the branding
        :rtype: set
        """
        # The editor is disabled when browsing in a non-default language, and
        # a test environment has no `lang` in its context.
        env = self.env(user=user, context={'lang': self.website.default_lang_id.code})
        with MockRequest(env, website=self.website):
            html = str(env['ir.qweb']._render(self.page_view.id, {
                'main_object': self.main_object.with_user(user),
            }))
        return {int(view_id) for view_id in re.findall(r'data-oe-id="(\d+)"', html)}

    def test_04_restricted_editor_partial_branding(self):
        branded_view_ids = self._branded_view_ids(self.restricted_editor)
        self.assertIn(self.writable_view.id, branded_view_ids)
        self.assertNotIn(self.forbidden_view.id, branded_view_ids)
