# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from werkzeug.exceptions import NotFound
import base64
import io
from PIL import Image
from lxml import etree, html

from odoo import Command
from odoo.orm.utils import ValidationError
from odoo.tests import HttpCase, tagged
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale.controllers.main import WebsiteSale


@tagged('post_install', '-at_install')
class TestWebsiteSaleGMCCommon(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.WebsiteSaleController = WebsiteSale()
        cls.website = cls.env['website'].browse(1)
        cls.website.domain = cls.base_url()
        cls.website.enabled_gmc_src = True
        cls.color_attribute = cls.env['product.attribute'].create({
            'name': 'Color',
            'value_ids': [
                Command.create({ 'name': 'white', 'sequence': 1 }),
                Command.create({ 'name': 'black', 'sequence': 2, 'default_extra_price': 20.0 }),
            ],
        })
        (
            cls.color_attribute_white,
            cls.color_attribute_black,
        ) = cls.color_attribute.value_ids
        (
            elec_root,
            elec_acc_sub,
            computer_acc,
            elec_acc_root,
            computer_comp,
            input_devices,
        ) = cls.env['product.public.category'].create([
            { 'name': 'Electronics' },
            { 'name': 'Electronics Accessories' },
            { 'name': 'Computer Accessories', 'sequence': 2 },
            { 'name': 'Electronics Accessories' },
            { 'name': 'Computer Components' },
            { 'name': 'Input Devices', 'sequence': 1 },
        ])
        computer_acc.parent_id = elec_acc_sub
        elec_acc_sub.parent_id = elec_root
        input_devices.parent_id = computer_comp
        computer_comp.parent_id = elec_acc_root
        cls.public_categories = computer_acc + input_devices
        cls.mouse_template = cls.env['product.template'].create({
            'name': 'Ergonomic Mouse',
            'list_price': 79.0,
            'is_published': True,
            'public_categ_ids': cls.public_categories.ids,
            'attribute_line_ids': [Command.create({
                'attribute_id': cls.color_attribute.id,
                'value_ids': [Command.set([
                    cls.color_attribute_white.id,
                    cls.color_attribute_black.id,
                ])],
            })],
        })
        (
            cls.mouse_white,
            cls.mouse_black,
        ) = cls.products = cls.mouse_template.product_variant_ids
        cls.mouse_white.write({
            'code': 'MAGIC-W',
            'barcode': '0195949655968',
            'description_ecommerce': 'An incredibly ergonomic mouse (just unusable when charged).',
        })
        cls.eur_currency = cls.env['res.currency'].search([
            ('name', '=', 'EUR'),
        ])
        cls.eur_currency.active = True
        cls.christmas_pricelist = cls.env['product.pricelist'].create({
            'name': 'Christmas Sales',
            'currency_id': cls.eur_currency.id,
            'item_ids': [
                Command.create({
                    'display_applied_on': '1_product',
                    'product_tmpl_id': cls.mouse_template.id,
                    'compute_price': 'percentage',
                    'percent_price': 10.0,
                    'date_start': datetime.datetime(2024, 12, 1, 0, 0),
                    'date_end': datetime.datetime(2024, 12, 31, 23, 59),
                })
            ]
        })
        cls.public_user = cls.env.ref('base.public_user')
        cls.delivery_carriers = cls.env['delivery.carrier'].search([('active', '=', True)])
        cls.delivery_countries = cls.env['res.country'].search([('code', 'in', ('BE', 'LU', 'GB'))])
        cls.delivery_carriers.country_ids = cls.delivery_countries
        cls.default_language = cls.website.language_ids[0]

    def mock_public_request(self):
        return MockRequest(
            self.mouse_template.with_user(self.public_user).env, 
            website=self.website.with_user(self.public_user),
        )

@tagged('post_install', '-at_install')
class TestWebsiteSaleGMCController(TestWebsiteSaleGMCCommon):

    def test_gmc_src_not_enabled(self):
        self.website.enabled_gmc_src = False
        with self.assertRaises(NotFound):
            with self.mock_public_request():
                self.WebsiteSaleController.products_xml_index()

    def test_gmc_no_domain_set(self):
        self.website.domain = False
        with self.assertRaises(ValidationError):
            with self.mock_public_request():
                self.WebsiteSaleController.products_xml_index()

    def test_gmc_route(self):
        response = self.url_open('/gmc.xml')
        self.assertEqual(200, response.status_code)
        gmc_xml = etree.fromstring(response.content) # valid xml

        self.assertEqual(f'Home | {self.website.name}', gmc_xml.xpath('//title')[0].text)
        self.assertEqual(
            f'{self.website.domain}/{self.default_language.url_code}', 
            gmc_xml.xpath('//link')[0].text,
        )
        self.assertEqual(
            'This is the homepage of the website', 
            gmc_xml.xpath('//description')[0].text,
        )

@tagged('post_install', '-at_install')
class TestWebsiteSaleGMCValues(TestWebsiteSaleGMCCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def update_values(self):
        with self.mock_public_request():
            self.values = self.products._get_gmc_values()
        self.white_mouse_values = self.values[self.mouse_white]
        self.black_mouse_values = self.values[self.mouse_black]

    def test_00_gmc_product_id(self):
        self.update_values()
        self.assertIn('id', self.white_mouse_values, 'An `id` is required.')
        self.assertIn('id', self.black_mouse_values, 'An `id` is required.')
        self.assertEqual(
            self.mouse_white.code, 
            self.white_mouse_values['id'], 
            '`id` should use the internal reference if it exists',
        )
        self.assertEqual(self.mouse_black.id, self.black_mouse_values['id'])
    
    def test_01_gmc_product_meta_info(self):
        self.update_values()
        self.assertIn('title', self.white_mouse_values, 'The `title` is required.')
        self.assertIn('description', self.white_mouse_values, 'A `description` is required.')
        self.assertIn('title', self.black_mouse_values, 'The `title` is required.')
        self.assertIn('description', self.black_mouse_values, 'A `description` is required.')
    
    def test_02_gmc_product_link(self):
        self.update_values()
        self.assertIn('link', self.white_mouse_values, 'A `link` to the product page is required.')
        response = self.url_open(self.white_mouse_values['link'])
        self.assertEqual(200, response.status_code)
        self.assertURLEqual(
            self.mouse_white.website_url, 
            response.url, 
            'Customer should be redirected to the product page',
        )
        response = self.url_open(self.black_mouse_values['link'])
        self.assertEqual(200, response.status_code)
        self.assertURLEqual(
            self.mouse_black.website_url, 
            response.url, 
            'Customer should be redirected to the product page',
        )

    def test_03_gmc_product_prices(self):
        self.update_values()
        self.assertIn('price', self.white_mouse_values, 'The `price` field is required.')
        self.assertIn('price', self.black_mouse_values, 'The `price` field is required.')
        response = self.url_open(self.white_mouse_values['link'])
        white_mouse_page = html.fromstring(response.content)
        white_mouse_price = white_mouse_page.xpath('//span[@itemprop="price"]')[0].text
        white_mouse_currency = white_mouse_page.xpath('//span[@itemprop="priceCurrency"]')[0].text
        self.assertEqual(
            self.white_mouse_values['price'], 
            f'{float(white_mouse_price)} {white_mouse_currency}', 
            'Price send to Google should match the price on the website',
        )
        response = self.url_open(self.black_mouse_values['link'])
        black_mouse_page = html.fromstring(response.content)
        black_mouse_price = black_mouse_page.xpath('//span[@itemprop="price"]')[0].text
        black_mouse_currency = black_mouse_page.xpath('//span[@itemprop="priceCurrency"]')[0].text
        self.assertEqual(
            self.black_mouse_values['price'], 
            f'{float(black_mouse_price)} {black_mouse_currency}', 
            'Price send to Google should match the price on the website',
        )

    def test_04_gmc_product_images(self):
        f = io.BytesIO()
        Image.new('RGB', (1920, 1080), 'green').save(f, 'JPEG')
        f.seek(0)
        self.image_template = base64.b64encode(f.read())
        f = io.BytesIO()
        Image.new('RGB', (1920, 1080), 'white').save(f, 'JPEG')
        f.seek(0)
        self.image_white_mouse = base64.b64encode(f.read())
        f = io.BytesIO()
        Image.new('RGB', (1920, 1080), 'red').save(f, 'JPEG')
        f.seek(0)
        self.extra_image_template = base64.b64encode(f.read())
        f = io.BytesIO()
        Image.new('RGB', (1920, 1080), 'black').save(f, 'JPEG')
        f.seek(0)
        self.extra_image_black_mouse = base64.b64encode(f.read())

        self.mouse_template.write({
            'image_1920': self.image_template,
            'product_template_image_ids': [
                Command.create({
                    'name': 'ergo_mouse_extra_image',
                    'image_1920': self.extra_image_template,
                })
            ]
        })
        self.mouse_white.write({
            'image_variant_1920': self.image_white_mouse,
        })
        self.mouse_black.write({
            'product_variant_image_ids': [
                Command.create({
                    'name': 'black_mouse_extra_image',
                    'image_1920': self.extra_image_black_mouse,
                })
            ]
        })
        self.update_values()
        self.assertIn('image_link', self.white_mouse_values, 'An `image_link` is required.')
        self.assertIn('image_link', self.black_mouse_values, 'An `image_link` is required.')
        self.assertEqual(
            1,
            len(self.white_mouse_values['additionnal_image_link']), 
            'Since it inherits from the mouse template, it should have its extra image.',
        )
        self.assertEqual(
            2,
            len(self.black_mouse_values['additionnal_image_link']), 
            'Since it inherits from the mouse template, it should have its extra image, plus the '
            'variant specific extra image.',
        )
        response = self.url_open(self.white_mouse_values['image_link'])
        response_image = base64.encodebytes(response.content).replace(b'\n', b'')
        self.assertEqual(
            response_image, 
            self.image_white_mouse, 
            'White mouse has a variant image, so it should be used.',
        )
        response = self.url_open(self.black_mouse_values['image_link'])
        response_image = base64.encodebytes(response.content).replace(b'\n', b'')
        self.assertEqual(
            response_image, 
            self.image_template, 
            'Black mouse does not have a variant image, should fall back to the template image.',
        )
        response = self.url_open(self.white_mouse_values['additionnal_image_link'][0])
        response_image = base64.encodebytes(response.content).replace(b'\n', b'')
        self.assertEqual(
            response_image, 
            self.extra_image_template,
            'If the template has some extra image, and there is space left for additionnal images '
            '(limited to 5), then it should use them.',
        )
        response = self.url_open(self.black_mouse_values['additionnal_image_link'][0])
        response_image = base64.encodebytes(response.content).replace(b'\n', b'')
        self.assertEqual(
            response_image, 
            self.extra_image_black_mouse, 
            'Black mouse does have a variant extra image, so it should be first in the list.',
        )
        response = self.url_open(self.black_mouse_values['additionnal_image_link'][1])
        response_image = base64.encodebytes(response.content).replace(b'\n', b'')
        self.assertEqual(
            response_image, 
            self.extra_image_template, 
            'If the template has some extra image, and there is space left for additionnal images '
            '(limited to 5), then it should use them.',
        )

        self.mouse_black.write({
            'product_variant_image_ids': [
                Command.create({
                    'name': f'image {i}',
                    'image_1920': self.extra_image_black_mouse,
                })
                for i in range(9) # add 9 more, total = 10 + template extra image = 11
            ]
        })
        self.update_values()
        self.assertEqual(
            10,
            len(self.black_mouse_values['additionnal_image_link']),
            'Google supports up to 10 additionnal images',
        )

    def test_05_gmc_product_identifier(self):
        self.update_values()
        self.assertEqual(
            self.mouse_white.barcode, 
            self.white_mouse_values['gtin'], 
            'If the product has a barcode, then it should be sent as `gtin`',
        )
        self.assertEqual(
            'yes',
            self.white_mouse_values['identifier_exists'],
            'White mouse does have an identifier, so it should be told to Google',
        )
        self.assertNotIn(
            'gtin',
            self.black_mouse_values,
            'Black mouse does not have any identifier, so it should be told to Google',
        )
        self.assertEqual(
            'no',
            self.black_mouse_values['identifier_exists'],
            'Black mouse does not have any identifier, so it should be specified to Google',
        )

    def test_06_gmc_product_type(self):
        self.update_values()
        self.assertListEqual(
            list(self.public_categories.sorted('sequence').mapped('name')),
            self.white_mouse_values['product_type'],
            'Product type should follow the sequence order as the first in the list will have the '
            'most impact in Google algorithms',
        )
        self.mouse_template.write({
            'public_categ_ids': [
                Command.create({ 'name': f'Category {i}' })
                for i in range(5)  # add 5 more, total = 7
            ]
        })
        self.update_values()
        self.assertEqual(
            5,
            len(self.white_mouse_values['product_type']),
            'Google supports up to 5 product type.',
        )

    def test_07_gmc_product_variants(self):
        some_attribute = self.env['product.attribute'].create([
            {
                'name': 'Color',
                'value_ids': [Command.create({ 'name': 'white', 'sequence': 1 })],
            },
            {
                'name': 'Material',
                'value_ids': [Command.create({ 'name': 'wood', 'sequence': 1 })],
            },
        ])
        product_no_variant = self.env['product.product'].create({
            'name': 'Test product',
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attr.id,
                    'value_ids': [Command.set(attr.value_ids.ids)],
                })
                for attr in some_attribute
            ],
            'list_price': 49.0,
            'is_published': True,
        })
        self.products |= product_no_variant
        self.update_values()
        self.assertEqual(
            self.mouse_template.id,
            self.white_mouse_values['item_group_id'],
            'This white mouse is a variant, so it should be linked to its template.',
        )
        self.assertEqual(
            self.mouse_template.id,
            self.black_mouse_values['item_group_id'],
            'This black mouse is a variant, so it should be linked to its template.',
        )
        self.assertNotIn(
            'item_group_id',
            self.values[product_no_variant],
            'A product that has no variant, or only one with attributes, should not be linked to a '
            'group.'
        )

    def test_08_gmc_product_bundles(self):
        keyboard = self.env['product.product'].create({
            'name': 'Keybaord',
            'list_price': 129.0,
        })
        product_bundle = self.env['product.product'].create({
            'name': 'Keyboard + Mouse',
            'type': 'combo',
            'combo_ids': [
                Command.create({
                    'name': 'Keyboard + Mouse Combo',
                    'combo_item_ids': [keyboard.id, self.mouse_white.id],
                })
            ],
            'list_price': 199.0,
        })
        self.products |= product_bundle
        self.update_values()

        self.assertEqual(
            'yes',
            self.values[product_bundle]['is_bundle'],
            'Combo products should be considered as bundles in Google.',
        )
        self.assertEqual(
            'no',
            self.white_mouse_values['is_bundle'],
            'Consu products should not be considered as bundles in Google.',
        )
        
    def test_09_gmc_product_labels(self):
        tags = [f'tag {i}' for i in range(10)]
        self.mouse_template.write({
            'product_tag_ids': [
                Command.create({ 'name': tag, 'sequence': i })
                for i, tag in enumerate(tags)
            ]
        })
        self.update_values()
        self.assertEqual(
            5,
            len(self.white_mouse_values['custom_label']),
            'Google only supports up to 5 custom labels',
        )
        self.assertListEqual(
            tags[:5],
            list(name for _, name in self.white_mouse_values['custom_label']),
            'Since we are limited, take the highest priority ones according to `sequence`',
        )

    def test_10_gmc_product_shipping(self):
        ...

    def test_11_gmc_product_availability(self):
        self.update_values()
        self.assertEqual(
            'in£_stock',
            self.white_mouse_values['availability'],
            'The availability should always be `in_stock`. (Could be overiden in `stock` module)',
        )

    def test_12_gmc_product_unit_pricing(self):
        ...
