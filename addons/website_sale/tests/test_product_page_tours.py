from odoo import Command
from odoo.tests import tagged, HttpCase
from odoo.addons.website_sale.controllers.main import WebsiteSale


@tagged('post_install', '-at_install')
class WebsiteSaleProductTestTours(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.WebsiteSaleController = WebsiteSale()
        cls.website = cls.env.ref('website.default_website')
        cls.website.company_id = cls.env.company

    def test_variant_extra_field_rendering(self):
        color_attribute = self.env['product.attribute'].create({
            'name': 'Color',
            'value_ids': [
                Command.create({'name': 'red', 'sequence': 1}),
                Command.create({'name': 'green', 'sequence': 2}),
                Command.create({'name': 'blue', 'sequence': 3}),
            ],
        })
        (red, green, blue) = color_attribute.value_ids

        led_tmpl = self.env['product.template'].create({
            'name': 'LED',
            'is_published': True,
            'attribute_line_ids': [Command.create({
                'attribute_id': color_attribute.id,
                'value_ids': [Command.link(color.id) for color in (red, green, blue)],
            })],
        })
        code_field = self.env['ir.model.fields'].search(['&', ('name', '=', 'default_code'), ('model_id.model', '=', 'product.template')])

        self.website.write({
            'shop_extra_field_ids': [Command.create({'field_id': code_field.id})],
        })

        led_variants = led_tmpl.product_variant_ids
        for i, variant in enumerate(led_variants):
            variant.default_code = f"LED0{i + 1}"

        self.start_tour(f'/shop/led-{led_tmpl.id}', 'variant_extra_fields_tour')
