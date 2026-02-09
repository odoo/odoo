# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.fields import Command, Date
from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


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

    def test_markup_data_uses_group_schema_when_multiple_variants(self):
        product_attribute = self.env['product.attribute'].create({
            'name': 'Test attribute',
            'create_variant': 'always',
            'value_ids': [
                Command.create({'name': 'Test value 1'}),
                Command.create({'name': 'Test value 2'}),
            ],
        })
        product_template = self.env['product.template'].create({
            'name': 'Test product',
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': product_attribute.id,
                    'value_ids': [Command.set(product_attribute.value_ids.ids)],
                }),
            ],
        })
        website = self.website
        with MockRequest(website.env, website=website):
            markup_data = product_template._to_markup_data(self.website)
        self.assertEqual(markup_data['@type'], 'ProductGroup')
        self.assertEqual(len(markup_data['hasVariant']), 2)

    def test_markup_data_uses_product_schema_when_single_variant(self):
        product_template = self.env['product.template'].create({'name': 'Test product'})
        website = self.website
        with MockRequest(website.env, website=website):
            markup_data = product_template._to_markup_data(self.website)
        self.assertEqual(markup_data['@type'], 'Product')

    def test_markup_data_uses_taxes_excluded_price_when_configured_on_website(self):
        self.env['res.config.settings'].create({
            'show_line_subtotals_tax_selection': 'tax_excluded'
        }).execute()
        with MockRequest(self.website.env, website=self.website):
            markup_data = self.product._to_markup_data(self.website)
            self.assertEqual(
                markup_data['offers']['price'],
                self.website.currency_id.round(self.product.base_unit_price),
            )

    def test_markup_data_uses_taxes_included_price_when_configured_on_website(self):
        self.env['res.config.settings'].create({
            'show_line_subtotals_tax_selection': 'tax_included'
        }).execute()
        self.product.price_extra = 10
        with MockRequest(self.website.env, website=self.website):
            product_tmpl = self.product.product_tmpl_id
            markup_data = self.product._to_markup_data(self.website)
            self.assertEqual(
                markup_data['offers']['price'],
                self.website.currency_id.round(
                    self.product.base_unit_price * (1 + product_tmpl.taxes_id[0].amount / 100)
                ),
            )

    def test_markup_data_converts_price_to_website_currency(self):
        company_currency = self.env.company.currency_id
        # Find a currency different from the company currency.
        self.website.currency_id = self.env['res.currency'].with_context(active_test=False).search([
            ('name', '!=', company_currency.name)
        ], limit=1)
        with MockRequest(self.env, website=self.website):
            markup = self.product._to_markup_data(self.website)
        # Expected converted price
        expected_price = company_currency._convert(
            self.product.list_price,
            self.website.currency_id,
            company=self.env.company,
            date=Date.from_string('2020-01-01'),
        )
        self.assertAlmostEqual(markup['offers']['price'], expected_price, places=2)

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

    def test_get_additionnal_combination_info_converts_price_to_website_currency(self):
        company_currency = self.env.company.currency_id
        # Find a currency different from the company currency.
        self.website.currency_id = self.env['res.currency'].with_context(active_test=False).search([
            ('name', '!=', company_currency.name)
        ], limit=1)
        with MockRequest(self.env, website=self.website):
            result = self.env['product.template']._get_additionnal_combination_info(
                self.product, 1.0, self.product.uom_id, Date.from_string('2020-01-01'), self.website
            )
        # Expected converted price
        expected_price = company_currency._convert(
            self.product.list_price,
            self.website.currency_id,
            company=self.env.company,
            date=Date.from_string('2020-01-01'),
        )
        self.assertAlmostEqual(result['price'], expected_price, places=2)
