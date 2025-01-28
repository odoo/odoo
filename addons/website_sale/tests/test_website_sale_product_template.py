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
        markup_data = product_template._to_markup_data(self.website)
        self.assertEqual(markup_data['@type'], 'ProductGroup')
        self.assertEqual(len(markup_data['hasVariant']), 2)

    def test_markup_data_uses_product_schema_when_single_variant(self):
        product_template = self.env['product.template'].create({'name': 'Test product'})
        markup_data = product_template._to_markup_data(self.website)
        self.assertEqual(markup_data['@type'], 'Product')
