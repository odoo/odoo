# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestShopSearchOrder(WebsiteSaleCommon):

    def _shop_search_order(self, order):
        """Return the ORDER BY the shop builds for the given `order` parameter."""
        with MockRequest(self.env, website=self.website):
            return WebsiteSale()._get_search_order({'order': order})

    def test_malformed_order_falls_back_to_default_sorting(self):
        """A term that is not a product field must not reach the ORDER BY.

        The shop searches `product.template` only, and the ORM raises a
        `ValueError` as soon as an order term is not a field of that model,
        which turned `/shop?order=<random number>` into a 500.
        """
        default_order = self._shop_search_order(None)
        for order in (
            '999608298',  # observed in production
            'name desc, 42',
            'no_such_field',
            'name sideways',
            'name desc,',
            # A '%2B' in the query string decodes to a literal '+', which is
            # not a field separator: 4000 requests per day sort the shop with
            # 'list_price+desc' and error out on the 150 ones sent encoded.
            'list_price+desc',
        ):
            with self.subTest(order=order):
                self.assertEqual(self._shop_search_order(order), default_order)

    def test_valid_order_is_preserved(self):
        for order in ('list_price desc', 'name asc', 'categ_id.id desc'):
            with self.subTest(order=order):
                self.assertIn(order, self._shop_search_order(order))

    def test_built_order_can_sort_products(self):
        """Sorting the products with a built order must not raise."""
        for order in ('999608298', 'list_price desc', None):
            with self.subTest(order=order):
                built = self._shop_search_order(order)
                self.env['product.template'].search([], order=built, limit=1)
