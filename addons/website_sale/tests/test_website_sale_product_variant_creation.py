# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tagged('post_install', '-at_install')
class TestWebsiteSaleProductVariantCreation(HttpCaseWithUserDemo):

    def test_dynamic_variant_not_created_on_ecommerce_view(self):
        """Ensure browsing does not create dynamic variants before add-to-cart."""
        color_attribute = self.env['product.attribute'].create({
            'name': 'Test Color Dynamic',
            'create_variant': 'dynamic',
            'value_ids': [
                Command.create({'name': 'Red'}),
                Command.create({'name': 'Blue'}),
            ],
        })
        color_red = color_attribute.value_ids.filtered(lambda value: value.name == 'Red')
        color_blue = color_attribute.value_ids.filtered(lambda value: value.name == 'Blue')

        product_template = self.env['product.template'].create({
            'name': 'T-Shirt Dynamic Tour',
            'type': 'consu',
            'list_price': 50.0,
            'is_published': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': color_attribute.id,
                    'value_ids': [
                        Command.link(color_red.id),
                        Command.link(color_blue.id),
                    ],
                }),
            ],
        })

        self.start_tour('/', 'website_sale_dynamic_variant_not_created_on_ecommerce_view', login='')

        final_variant_count = len(product_template.product_variant_ids)
        self.assertEqual(
            final_variant_count,
            0,
            "Viewing the product page must not create variants.",
        )
