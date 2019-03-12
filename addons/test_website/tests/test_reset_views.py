# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

import odoo.tests
from odoo.tools import mute_logger


def break_view(view, fr='<p>placeholder</p>', to='<p t-field="not.exist"/>'):
    view.arch = view.arch.replace(fr, to)


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteResetViews(odoo.tests.HttpCase):
    def do_test(self, name):
        self.browser_js(
            "/",
            "odoo.__DEBUG__.services['web_tour.tour'].run('%s')" % name,
            "odoo.__DEBUG__.services['web_tour.tour'].tours.%s.ready" % name,
            login="admin"
        )

    def fix_it(self, page):
        self.authenticate("admin", "admin")
        resp = self.url_open(page)
        self.assertEqual(resp.status_code, 500, "Waiting 500")
        self.assertTrue('<button id="reset_templates_button"' in resp.text)
        data = {'templates': [self.find_template(resp)], 'redirect': page}
        resp = self.url_open('/website/reset_templates', data)
        self.assertEqual(resp.status_code, 200, "Waiting 200")

    def find_template(self, response):
        find = re.search(r'<input.*type="checkbox".*name="templates".*value="([0-9]+)?"', response.text)
        return find and find.group(1)

    def setUp(self):
        super(TestWebsiteResetViews, self).setUp()
        self.Website = self.env['website']
        self.View = self.env['ir.ui.view']
        self.test_view = self.Website.viewref('test_website.test_view')

    @mute_logger('odoo.addons.website.models.ir_http')
    def test_01_reset_specific_page_view(self):
        self.test_page_view = self.Website.viewref('test_website.test_page_view')
        total_views = self.View.search_count([('type', '=', 'qweb')])
        # Trigger COW then break the QWEB XML on it
        break_view(self.test_page_view.with_context(website_id=1))
        self.assertEqual(total_views + 1, self.View.search_count([('type', '=', 'qweb')]), "Missing COW view")
        self.fix_it('/test_page_view')

    @mute_logger('odoo.addons.website.models.ir_http')
    def test_02_reset_specific_view_controller(self):
        total_views = self.View.search_count([('type', '=', 'qweb')])
        # Trigger COW then break the QWEB XML on it
        break_view(self.test_view.with_context(website_id=1))
        self.assertEqual(total_views + 1, self.View.search_count([('type', '=', 'qweb')]), "Missing COW view")
        self.fix_it('/test_view')

    @mute_logger('odoo.addons.website.models.ir_http')
    def test_03_reset_specific_view_controller_t_called(self):
        self.test_view_to_be_t_called = self.Website.viewref('test_website.test_view_to_be_t_called')

        total_views = self.View.search_count([('type', '=', 'qweb')])
        # Trigger COW then break the QWEB XML on it
        break_view(self.test_view_to_be_t_called.with_context(website_id=1))
        break_view(self.test_view, to='<t t-call="test_website.test_view_to_be_t_called"/>')
        self.assertEqual(total_views + 1, self.View.search_count([('type', '=', 'qweb')]), "Missing COW view")
        self.fix_it('/test_view')

    @mute_logger('odoo.addons.website.models.ir_http')
    def test_04_reset_specific_view_controller_inherit(self):
        self.test_view_child_broken = self.Website.viewref('test_website.test_view_child_broken')

        # Activate and break the inherited view
        self.test_view_child_broken.active = True
        break_view(self.test_view_child_broken.with_context(website_id=1, load_all_views=True))

        self.fix_it('/test_view')

    # This test work in real life, but not in test mode since we cannot rollback savepoint.
    # @mute_logger('odoo.addons.website.models.ir_http', 'odoo.addons.website.models.ir_ui_view')
    # def test_05_reset_specific_view_controller_broken_request(self):
    #     total_views = self.View.search_count([('type', '=', 'qweb')])
    #     # Trigger COW then break the QWEB XML on it
    #     break_view(self.test_view.with_context(website_id=1), to='<t t-esc="request.env[\'website\'].browse(\'a\').name" />')
    #     self.assertEqual(total_views + 1, self.View.search_count([('type', '=', 'qweb')]), "Missing COW view (1)")
    #     self.fix_it('/test_view')

    # also mute ir.ui.view as `get_view_id()` will raise "Could not find view object with xml_id 'not.exist'""
    @mute_logger('odoo.addons.website.models.ir_http', 'odoo.addons.website.models.ir_ui_view')
    def test_06_reset_specific_view_controller_inexisting_template(self):
        total_views = self.View.search_count([('type', '=', 'qweb')])
        # Trigger COW then break the QWEB XML on it
        break_view(self.test_view.with_context(website_id=1), to='<t t-call="not.exist"/>')
        self.assertEqual(total_views + 1, self.View.search_count([('type', '=', 'qweb')]), "Missing COW view (2)")
        self.fix_it('/test_view')

    @mute_logger('odoo.addons.website.models.ir_http')
    def test_07_reset_page_view_complete_flow(self):
        self.do_test('test_reset_page_view_complete_flow_part1')
        self.fix_it('/test_page_view')
        self.do_test('test_reset_page_view_complete_flow_part2')
        self.fix_it('/test_page_view')
