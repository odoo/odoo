from odoo.tests.common import tagged
from odoo.tests import HttpCase


@tagged('post_install', '-at_install')
class TestWebsiteStudioControllers(HttpCase):
    def test_new_form_collision(self):
        self.start_tour("/web?debug=tests", 'website_studio_new_form_page_collision_tour', login="admin", timeout=200)
        last_website_page = self.env['website.page'].search([], order='id desc', limit=1)
        self.assertEqual(last_website_page.name, 'web Form', "The new page should have the correct display name")
        self.assertEqual(last_website_page.url, '/web-form', "The new page should have the correct url")
