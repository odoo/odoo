# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleProductTemplate(WebsiteSaleCommon):

    def test_website_sale_get_configurator_display_price(self):
        self.website.show_line_subtotals_tax_selection = 'tax_included'
        tax = self.env['account.tax'].create({'name': "Test tax", 'amount': 10})
        product = self._create_product(list_price=100, taxes_id=[Command.link(tax.id)])

        env = self.env(user=self.public_user)
        with MockRequest(env, website=self.website.with_env(env)):
            configurator_price = self.env['product.template']._get_configurator_display_price(
                product_or_template=product,
                quantity=3,
                date=datetime(2000, 1, 1),
                currency=self.currency,
                pricelist=self.pricelist,
            )

        self.assertEqual(configurator_price[0], 110)

    def test_website_sale_get_additional_configurator_data(self):
        product_category = self.env['product.category'].create({'name': "Test category"})
        product = self._create_product(categ_id=product_category.id)
        currency_eur = self._enable_currency('EUR')

        env = self.env(user=self.public_user)
        with MockRequest(env, website=self.website.with_env(env)):
            configurator_data = self.env['product.template']._get_additional_configurator_data(
                product_or_template=product,
                date=datetime(2000, 1, 1),
                currency=currency_eur,
                pricelist=self.pricelist,
            )

        self.assertEqual(configurator_data['category_name'], "Test category")
        self.assertEqual(configurator_data['currency_name'], 'EUR')

    def test_remove_archived_products_from_cart(self):
        """Archived products shouldn't appear in carts"""
        self.product.action_archive()
        self.assertNotIn(
            self.product, self.cart.order_line.product_id,
            "Archived product should be deleted from the cart.",
        )
        self.service_product.product_tmpl_id.action_archive()
        self.assertNotIn(
            self.service_product, self.cart.order_line.product_id,
            "All products from archived product templates should be removed from the cart.",
        )
