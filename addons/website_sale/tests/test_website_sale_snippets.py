# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import logging

from PIL import Image

from odoo.tests import Command, HttpCase, tagged
from odoo.addons.website.tools import MockRequest


_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install', 'website_snippets')
class TestSnippets(HttpCase):

    def test_01_snippet_products_edition(self):
        self.env['product.product'].create({
            'name': 'Test Product',
            'website_published': True,
            'sale_ok': True,
            'list_price': 500,
        })
        self.env['product.product'].create({
            'name': 'Test Product 2',
            'website_published': True,
            'sale_ok': True,
            'list_price': 500,
        })
        self.env['product.product'].create({
            'name': 'Test Product 3',
            'website_published': True,
            'sale_ok': True,
            'list_price': 500,
        })
        self.env['product.product'].create({
            'name': 'Test Product 4',
            'website_published': True,
            'sale_ok': True,
            'list_price': 500,
        })
        self.start_tour('/', 'website_sale.snippet_products', login='admin')

    def test_02_snippet_products_remove(self):
        Visitor = self.env['website.visitor']
        user = self.env['res.users'].search([('login', '=', 'admin')])
        website_visitor = Visitor.search([('partner_id', '=', user.partner_id.id)])
        if not website_visitor:
            with MockRequest(user.with_user(user).env, website=self.env['website'].get_current_website()):
                website_visitor = Visitor.create({'partner_id': user.partner_id.id})
        self.assertEqual(website_visitor.name, user.name, "The visitor should be linked to the admin user, not OdooBot or anything.")
        self.product = self.env['product.product'].create({
            'name': 'Storage Box',
            'website_published': True,
            'image_512': b'/product/static/img/product_product_9-image.jpg',
            'display_name': 'Bin',
            'description_sale': 'Pedal-based opening system',
        })
        before_tour_product_ids = website_visitor.product_ids.ids
        website_visitor._add_viewed_product(self.product.id)

        self.start_tour('/', 'website_sale.products_snippet_recently_viewed', login='admin')
        self.assertEqual(before_tour_product_ids, website_visitor.product_ids.ids, "There shouldn't be any new product in recently viewed after this tour")

    def test_03_shop_product_hover(self):
        product_attr_color = self.env['product.attribute'].create({
            'name': 'Color',
            'display_type': 'color',
            'show_variants': 'visible',
        })
        color_gray = self.env['product.attribute.value'].create({
            'name': 'Old Fashioned Gray',
            'attribute_id': product_attr_color.id,
            'html_color': '#808080',
        })
        color_blue = self.env['product.attribute.value'].create({
            'name': 'Electric Blue',
            'attribute_id': product_attr_color.id,
            'html_color': '#0000FF',
        })
        product_attr_legs = self.env['product.attribute'].create({
            'name': 'Legs',
            'display_type': 'radio',
            'show_variants': 'visible',
        })
        legs_steel = self.env['product.attribute.value'].create({
            'name': 'Steel',
            'attribute_id': product_attr_legs.id,
        })
        legs_aluminum = self.env['product.attribute.value'].create({
            'name': 'Aluminum',
            'attribute_id': product_attr_legs.id,
        })

        image_gray = self._create_image('#808080')
        image_blue = self._create_image('#0000FF')
        image_steel = self._create_image('#C0C0C0')
        image_aluminum = self._create_image('#D3D3D3')

        product_template = self.env['product.template'].create({
            'name': 'Test',
            'type': 'consu',
            'website_published': True,
            'product_template_image_ids': [
                Command.create({'name': 'Gray Image', 'image_1920': image_gray}),
                Command.create({'name': 'Blue Image', 'image_1920': image_blue}),
                Command.create({'name': 'Steel Image', 'image_1920': image_steel}),
                Command.create({'name': 'Aluminum Image', 'image_1920': image_aluminum}),
            ],
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': product_attr_color.id,
                    'value_ids': [(6, 0, [color_gray.id, color_blue.id])]
                }),
                Command.create({
                    'attribute_id': product_attr_legs.id,
                    'value_ids': [(6, 0, [legs_steel.id, legs_aluminum.id])],
                }),
            ],
        })

        product_template._create_variant_ids()

        for variant in product_template.product_variant_ids:
            if 'Old Fashioned Gray' in variant.product_template_attribute_value_ids.mapped('name'):
                variant.image_1920 = image_gray
            elif 'Electric Blue' in variant.product_template_attribute_value_ids.mapped('name'):
                variant.image_1920 = image_blue
            elif 'Steel' in variant.product_template_attribute_value_ids.mapped('name'):
                variant.image_1920 = image_steel
            elif 'Aluminum' in variant.product_template_attribute_value_ids.mapped('name'):
                variant.image_1920 = image_aluminum

        self.start_tour("/", 'website_sale_shop_products', login='admin')

    def _create_image(self, color):
        f = io.BytesIO()
        Image.new('RGB', (1920, 1080), color).save(f, 'JPEG')
        f.seek(0)
        return base64.b64encode(f.read())
