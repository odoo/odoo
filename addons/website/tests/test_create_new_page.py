# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestCreateNewPage(HttpCase):

    def test_create_new_page(self):
        self.start_tour('/', 'website_create_new_page', login='admin')
