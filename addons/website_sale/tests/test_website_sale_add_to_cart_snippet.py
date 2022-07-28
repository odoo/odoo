# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestAddToCartSnippet(HttpCase):
    def test_configure_product(self):
        self.start_tour("/", 'add_to_cart_snippet_tour', login="admin")
