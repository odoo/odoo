# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

import odoo.tests
from odoo.tools import mute_logger


def break_view(view, fr='<p>placeholder</p>', to='<p t-field="no_record.exist"/>'):
    view.arch = view.arch.replace(fr, to)


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteResetViews(odoo.tests.HttpCase):

    def fix_it(self, page, mode='soft'):
        self.authenticate("admin", "admin")
        resp = self.url_open(page)
        self.assertEqual(resp.status_code, 500, "Waiting 500")
        self.assertTrue('<button data-mode="soft" class="reset_templates_button' in resp.text)
        data = {'view_id': self.find_template(resp), 'redirect': page, 'mode': mode}
        resp = self.url_open('/website/reset_template', data)
        self.assertEqual(resp.status_code, 200, "Waiting 200")

    def find_template(self, response):
        find = re.search(r'<input.*type="hidden".*name="view_id".*value="([0-9]+)?"', response.text)
        return find and find.group(1)

    def setUp(self):
        super(TestWebsiteResetViews, self).setUp()
        self.Website = self.env['website']
        self.View = self.env['ir.ui.view']
        self.test_view = self.Website.viewref('test_website.test_view')

    @mute_logger('odoo.http')
    def test_01_reset_specific_page_view(self):
        self.test_page_view = self.Website.viewref('test_website.test_page_view')
        total_views = self.View.search_count([('type', '=', 'qweb')])
        # Trigger COW then break the QWEB XML on it
        break_view(self.test_page_view.with_context(website_id=1))
        self.assertEqual(total_views + 1, self.View.search_count([('type', '=', 'qweb')]), "Missing COW view")
        self.fix_it('/test_page_view')

    @mute_logger('odoo.http')
    def test_02_reset_specific_view_controller(self):
        total_views = self.View.search_count([('type', '=', 'qweb')])
        # Trigger COW then break the QWEB XML on it
        # `t-att-data="no_record.exist"` will test the case where exception.html contains branding
        break_view(self.test_view.with_context(website_id=1), to='<p t-att-data="no_record.exist" />')
        self.assertEqual(total_views + 1, self.View.search_count([('type', '=', 'qweb')]), "Missing COW view")
        self.fix_it('/test_view')

    @mute_logger('odoo.http')
    def test_03_reset_specific_view_controller_t_called(self):
        self.test_view_to_be_t_called = self.Website.viewref('test_website.test_view_to_be_t_called')

        total_views = self.View.search_count([('type', '=', 'qweb')])
        # Trigger COW then break the QWEB XML on it
        break_view(self.test_view_to_be_t_called.with_context(website_id=1))
        break_view(self.test_view, to='<t t-call="test_website.test_view_to_be_t_called"/>')
        self.assertEqual(total_views + 1, self.View.search_count([('type', '=', 'qweb')]), "Missing COW view")
        self.fix_it('/test_view')

    @mute_logger('odoo.http')
    def test_04_reset_specific_view_controller_inherit(self):
        self.test_view_child_broken = self.Website.viewref('test_website.test_view_child_broken')

        # Activate and break the inherited view
        self.test_view_child_broken.active = True
        break_view(self.test_view_child_broken.with_context(website_id=1, load_all_views=True))

        self.fix_it('/test_view')

    # This test work in real life, but not in test mode since we cannot rollback savepoint.
    # @mute_logger('odoo.http', 'odoo.addons.website.models.ir_ui_view')
    # def test_05_reset_specific_view_controller_broken_request(self):
    #     total_views = self.View.search_count([('type', '=', 'qweb')])
    #     # Trigger COW then break the QWEB XML on it
    #     break_view(self.test_view.with_context(website_id=1), to='<t t-esc="request.env[\'website\'].browse(\'a\').name" />')
    #     self.assertEqual(total_views + 1, self.View.search_count([('type', '=', 'qweb')]), "Missing COW view (1)")
    #     self.fix_it('/test_view')

    # also mute ir.ui.view as `_get_view_id()` will raise "Could not find view object with xml_id 'no_record.exist'""
    @mute_logger('odoo.http', 'odoo.addons.website.models.ir_ui_view')
    def test_06_reset_specific_view_controller_inexisting_template(self):
        total_views = self.View.search_count([('type', '=', 'qweb')])
        # Trigger COW then break the QWEB XML on it
        break_view(self.test_view.with_context(website_id=1), to='<t t-call="no_record.exist"/>')
        self.assertEqual(total_views + 1, self.View.search_count([('type', '=', 'qweb')]), "Missing COW view (2)")
        self.fix_it('/test_view')

    @mute_logger('odoo.http')
    def test_07_reset_page_view_complete_flow(self):
        self.start_tour(self.env['website'].get_client_action_url('/test_page_view'), 'test_reset_page_view_complete_flow_part1', login="admin")
        self.fix_it('/test_page_view')
        self.start_tour(self.env['website'].get_client_action_url('/test_page_view'), 'test_reset_page_view_complete_flow_part2', login="admin")
        self.fix_it('/test_page_view')

    @mute_logger('odoo.http')
    def test_08_reset_specific_page_view_hard_mode(self):
        self.test_page_view = self.Website.viewref('test_website.test_page_view')
        total_views = self.View.search_count([('type', '=', 'qweb')])
        # Trigger COW then break the QWEB XML on it
        break_view(self.test_page_view.with_context(website_id=1))
        # Break it again to have a previous arch different than file arch
        break_view(self.test_page_view.with_context(website_id=1))
        self.assertEqual(total_views + 1, self.View.search_count([('type', '=', 'qweb')]), "Missing COW view")
        with self.assertRaises(AssertionError):
            # soft reset should not be able to reset the view as previous
            # version is also broken
            self.fix_it('/test_page_view')
        self.fix_it('/test_page_view', 'hard')
        # hard reset should set arch_updated to false
        self.assertFalse(self.test_page_view.arch_updated)
