# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestWebsitePageProperties(HttpCase):

    def test_website_page_properties_common(self):
        self.start_tour('/test_view', 'website_page_properties_common', login='admin')

    def test_website_page_properties_can_publish(self):
        self.start_tour('/test_website/model_item/1', 'website_page_properties_can_publish', login='admin')

    def test_website_page_properties_website_page(self):
        self.start_tour('/', 'website_page_properties_website_page', login='admin')
