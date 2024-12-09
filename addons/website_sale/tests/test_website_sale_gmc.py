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
                Command.create({'name': 'white', 'sequence': 1}),
                Command.create({'name': 'black', 'sequence': 2, 'default_extra_price': 20.0}),
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
            { 'name': 'Computer Accessories' },
            { 'name': 'Electronics Accessories' },
            { 'name': 'Computer Components' },
            { 'name': 'Input Devices' },
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
        ) = cls.mouse_products = cls.mouse_template.product_variant_ids
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
        with MockRequest(
            cls.mouse_template.with_user(cls.public_user).env, 
            website=cls.website.with_user(cls.public_user),
        ):
            cls.values = cls.mouse_products._get_gmc_values()
        cls.white_mouse_values = cls.values[cls.mouse_white]
        cls.black_mouse_values = cls.values[cls.mouse_black]

    def test_00_gmc_product_id(self):
        self.assertEqual(
            self.mouse_white.code, 
            self.white_mouse_values['id'], 
            'ID should use the internal reference if it exists',
        )
    
    def test_01_gmc_product_meta_info(self):
        self.assertEqual(self.mouse_white.name, self.white_mouse_values['title'])
        # TODO: check description etc. every text
    
    def test_02_gmc_product_link(self):
        response = self.url_open(self.white_mouse_values['link'])
        self.assertEqual(200, response.status_code)
        self.assertURLEqual(
            self.mouse_white.website_url, 
            response.url, 
            'Customer should be redirected to the product page',
        )

    def test_03_gmc_product_prices(self):
        response = self.url_open(self.white_mouse_values['link'])
        white_mouse_page = html.fromstring(response.content)
        white_mouse_price = white_mouse_page.xpath('//span[@itemprop="price"]')[0].text
        white_mouse_currency = white_mouse_page.xpath('//span[@itemprop="priceCurrency"]')[0].text
        self.assertEqual(
            self.white_mouse_values['price'], 
            f'{float(white_mouse_price)} {white_mouse_currency}', 
            'Price send to Google should match the price on the website',
        )

    def test_04_gmc_product_images(self):
        # f = io.BytesIO()
        # Image.new('RGB', (1920, 1080), color_blue).save(f, 'JPEG')
        # f.seek(0)
        # blue_image = base64.b64encode(f.read())
        ...

    def test_05_gmc_product_identifier(self):
        ...

    def test_06_gmc_product_type(self):
        ...

    def test_07_gmc_product_variants(self):
        ...

    def test_08_gmc_product_bundles(self):
        ...
        
    def test_09_gmc_product_labels(self):
        ...

    def test_10_gmc_product_shipping(self):
        ...

    def test_11_gmc_product_availability(self):
        ...

    def test_11_gmc_product_unit_pricing(self):
        ...
