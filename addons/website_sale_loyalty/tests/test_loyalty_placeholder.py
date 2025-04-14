# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale_loyalty import ProductProduct


@tagged('post_install', '-at_install')
class TestLoyaltyPlaceholder(HttpCase):

    def test_loyalty_placeholder(self):
        """ Test that the loyalty placeholder image is accessible to all website visitors. """
        product_model = ProductProduct()

        with patch.object(product_model, '_can_return_content') as mock:
            product_model._get_product_placeholder_filename()
            self.assertEqual(
                mock.call_count,
                1,
                msg="Loyalty product images should be accessible regardless of access rights.",
            )
