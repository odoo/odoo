# coding: utf-8
from odoo.tests import tagged
from odoo.addons.website.tools import MockRequest
from odoo.addons.sale.tests.test_sale_product_attribute_value_config import TestSaleProductAttributeValueCommon

@tagged('post_install', '-at_install')
class WebsiteSaleProductTests(TestSaleProductAttributeValueCommon):

    def setUp(self):
        super().setUp()
        self.website = self.env.ref('website.default_website')

    def test_website_sale_contextual_price(self):
        contextual_price = self.computer._get_contextual_price()
        self.assertEqual(
            self.computer.list_price,
            contextual_price,
            "With no pricelist context, the contextual price should be the computer list price."
        )

        pricelist = self.env['product.pricelist'].create({
            'name': 'Base Pricelist',
            'sequence': 4,
        })

        # make sure the pricelist has a 10% discount
        self.env['product.pricelist.item'].create({
            'price_discount': 10,
            'compute_price': 'formula',
            'pricelist_id': pricelist.id,
        })
        discount_rate = 0.9
        currency_ratio = 2
        pricelist.currency_id = self._setup_currency(currency_ratio)
        with MockRequest(self.env, website=self.website):
            contextual_price = self.computer._get_contextual_price()
        self.assertEqual(
            2000.0 * currency_ratio * discount_rate, contextual_price,
            "With a website pricelist context, the contextual price should be the one defined for the website's pricelist."
        )

    def test_base_price_with_discount_on_pricelist_tax_included(self):
        """
        Tests that the base price of a product with tax included
        and discount from a price list is correctly displayed in the shop

        ex: A product with a price of $61.98 ($75 tax incl. of 21%) and a discount of 20%
        should display the base price of $75
        """
        self.env['res.config.settings'].create({                  # Set Settings:
            'show_line_subtotals_tax_selection': 'tax_included',  # Set "Tax Included" on the "Display Product Prices"
            'product_pricelist_setting': 'advanced',              # advanced pricelist (discounts, etc.)
            'group_product_price_comparison': True,               # price comparison
        }).execute()

        tax = self.env['account.tax'].create({
            'name': '21%',
            'type_tax_use': 'sale',
            'amount': 21,
        })
        product_tmpl = self.env['product.template'].create({
            'name': 'Test Product',
            'type': 'consu',
            'list_price': 61.98,  # 75 tax incl.
            'taxes_id': [(6, 0, [tax.id])],
            'is_published': True,
        })
        pricelist_item = self.env['product.pricelist.item'].create({
            'price_discount': 20,
            'compute_price': 'formula',
            'product_tmpl_id': product_tmpl.id,
        })
        current_website = self.env['website'].get_current_website()
        pricelist = current_website._get_current_pricelist()
        pricelist.item_ids = [(6, 0, [pricelist_item.id])]
        pricelist.discount_policy = 'without_discount'
        res = product_tmpl._get_sales_prices(pricelist, self.env['account.fiscal.position'])
        self.assertEqual(res[product_tmpl.id]['base_price'], 75)
