# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.website.tools import create_image_attachment

@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteGridLayout(odoo.tests.HttpCase):

    def test_01_replace_grid_image(self):
        create_image_attachment(self.env, '/web/image/website.s_banner_default_image', 's_banner_default_image.jpg')
        create_image_attachment(self.env, '/web/image/website.s_banner_default_image', 's_banner_default_image2.jpg')
        self.start_tour(self.env['website'].get_client_action_url('/'), 'website_replace_grid_image', login="admin")

    def test_02_scroll_to_new_grid_item(self):
        create_image_attachment(self.env, '/web/image/website.s_banner_default_image', 's_banner_default_image.jpg')
        self.start_tour(self.env['website'].get_client_action_url('/'), 'scroll_to_new_grid_item', login='admin')
