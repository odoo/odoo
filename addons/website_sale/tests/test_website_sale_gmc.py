# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import time
from datetime import datetime, timedelta
from lxml import etree
from PIL import Image
from werkzeug.exceptions import NotFound

from odoo import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale.controllers.main import WebsiteSale


@tagged('post_install', '-at_install')
class TestWebsiteSaleGMCCommon(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        cls.mouse_template = cls.env['product.template'].create({
            'name': 'Ergonomic Mouse',
            'list_price': 79.0,
            'is_published': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': cls.color_attribute.id,
                    'value_ids': [
                        Command.set([
                            cls.color_attribute_white.id,
                            cls.color_attribute_black.id,
                        ])
                    ],
                })
            ],
        })
        (
            cls.white_mouse,
            cls.black_mouse,
        ) = cls.mouse_template.product_variant_ids
        cls.white_mouse.write({
            'default_code': 'MAGIC-W',
            'barcode': '0195949655968',
            'description_ecommerce': 'An incredibly ergonomic mouse (just unusable when charged).',
        })
        cls.keyboard = cls.env['product.product'].create({
            'name': 'Keyboard',
            'list_price': 129.0,
            'is_published': True,
        })
        combo = cls.env['product.combo'].create({
            'name': 'Keybaord + Mouse Combo',
            'combo_item_ids': [
                Command.create({'product_id': cls.keyboard.id}),
                Command.create({'product_id': cls.white_mouse.id}),
            ],
        })
        cls.product_bundle = cls.env['product.product'].create({
            'name': 'Keyboard + Mouse bundle',
            'type': 'combo',
            'combo_ids': [Command.set(combo.ids)],
            'list_price': 199.0,
            'is_published': True,
        })
        cls.products = cls.white_mouse + cls.black_mouse + cls.keyboard + cls.product_bundle
        cls.eur_currency = cls.env['res.currency'].search([('name', '=', 'EUR')])
        cls.eur_currency.active = True
        cls.eur_currency.write({
            'rate_ids': [
                Command.clear(),
                Command.create({
                    'name': time.strftime('%Y-%m-%d'),
                    'rate': 1.1,
                })
            ],
        })
        cls.christmas_pricelist = cls.env['product.pricelist'].create({
            'name': 'EUR Christmas Sales',
            'currency_id': cls.eur_currency.id,
            'selectable': True,
            'item_ids': [
                Command.create({
                    'product_tmpl_id': cls.mouse_template.id,
                    'compute_price': 'percentage',
                    'percent_price': 10.0,
                    'date_start': datetime.now() - timedelta(1),
                    'date_end': datetime.now() + timedelta(1),
                }),
                Command.create({
                    'compute_price': 'percentage',
                    'percent_price': 0.0,
                }),
            ],
        })
        cls.public_user = cls.env.ref('base.public_user')
        cls.delivery_countries = cls.env['res.country'].search([('code', 'in', ('BE', 'LU', 'GB'))])
        # limit computation overhead
        cls.env['delivery.carrier'].search([]).country_ids = cls.delivery_countries
        cls.default_lang = cls.website.default_lang_id

    def mock_public_request(self, **kwargs):
        website = kwargs.pop('website', self.website)
        return MockRequest(
            self.products.with_user(self.public_user).env,
            website=website.with_user(self.public_user),
            **kwargs,
        )

    def update_items(self, **kwargs):
        with self.mock_public_request(**kwargs):
            self.items = self.products._get_gmc_items()
        self.white_mouse_item = self.items[self.white_mouse]
        self.black_mouse_item = self.items[self.black_mouse]


@tagged('post_install', '-at_install')
class TestWebsiteSaleGMCController(TestWebsiteSaleGMCCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.WebsiteSaleController = WebsiteSale()

    def test_gmc_src_not_enabled(self):
        """/gmc.xml route is accessible iff `website.enabled_gmc_src` is true"""
        self.website.enabled_gmc_src = False
        with self.assertRaises(NotFound), self.mock_public_request():
            self.WebsiteSaleController.gmc_data_source()

    def test_gmc_route(self):
        """Test /gm.xml works under normal conditions"""
        response = self.url_open('/gmc.xml')
        self.assertEqual(200, response.status_code)
        gmc_xml = etree.XML(response.content)  # valid xml

        self.assertEqual(f'Home | {self.website.name}', gmc_xml.xpath('//title')[0].text)
        self.assertURLEqual(
            '/',
            gmc_xml.xpath('//link')[0].text,
        )
        self.assertEqual(
            'This is the homepage of the website',
            gmc_xml.xpath('//description')[0].text,
        )

    def test_translation(self):
        """Test translation of /gmc.xml content"""
        fr_lang = self.env['res.lang']._activate_lang('fr_FR')
        self.website.language_ids += fr_lang
        self.website.name = 'The best website'
        self.website.with_context(lang=fr_lang.code).name = 'Mon unique site'
        self.white_mouse.with_context(lang=fr_lang.code).name = 'La souris magique blanche'
        response = self.url_open('/fr/gmc.xml')
        self.assertEqual(200, response.status_code)
        gmc_xml = etree.XML(response.content)
        self.assertEqual('Home | Mon unique site', gmc_xml.xpath('//title')[0].text)
        self.assertURLEqual(
            f'/{fr_lang.url_code}',
            gmc_xml.xpath('//link')[0].text,
            'The links must redirect to the french website.',
        )
        self.assertEqual(
            'La souris magique blanche',
            gmc_xml.xpath(
                '//item[g:id="MAGIC-W"]/g:title', namespaces={'g': 'http://base.google.com/ns/1.0'}
            )[0].text,
        )

    def test_pricelist(self):
        """Test /gmc.xml with a specific pricelist"""
        response = self.url_open('/gmc-eur%20christ.xml')
        self.assertEqual(200, response.status_code)
        gmc_xml = etree.XML(response.content)
        self.assertEqual(
            '86.9 EUR',
            gmc_xml.xpath(
                '//item[g:id="MAGIC-W"]/g:price', namespaces={'g': 'http://base.google.com/ns/1.0'}
            )[0].text
        )


@tagged('post_install', '-at_install')
class TestWebsiteSaleGMCItems(TestWebsiteSaleGMCCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_gmc_items_only_consu_or_combo(self):
        """Test `_get_gmc_items()` ignores services"""
        self.products += self.env['product.product'].create([{
            'name': 'Service Type Product',
            'type': 'service',
        }])
        *consu_combo, service_product = self.products
        self.update_items()
        self.assertNotIn(
            service_product, self.items, 'Services are not allowed in a product data source'
        )
        for prod in consu_combo:
            self.assertIn(
                prod,
                self.items,
                'Other types of products can be part of a product data source',
            )

    def test_gmc_product_id(self):
        """Test prefer internal code to database id"""
        self.update_items()
        self.assertIn('id', self.white_mouse_item, 'An `id` is required.')
        self.assertIn('id', self.black_mouse_item, 'An `id` is required.')
        self.assertEqual(
            self.white_mouse.code,
            self.white_mouse_item['id'],
            '`id` should use the internal reference if it exists',
        )
        self.assertEqual(self.black_mouse.id, self.black_mouse_item['id'])

    def test_gmc_product_required_field(self):
        """Test all required fields"""
        self.update_items()
        for item in self.items.values():
            self.assertLessEqual(
                {
                    'id',
                    'title',
                    'description',
                    'link',
                    'image_link',
                    'availability',
                    'price',
                    'identifier_exists',
                    'shipping',
                },
                item.keys(),
            )

    def test_gmc_product_link(self):
        """Test all link must redirect to the correct product"""
        self.update_items()
        self.assertIn('link', self.white_mouse_item, 'A `link` to the product page is required.')
        response = self.url_open(self.white_mouse_item['link'])
        self.assertEqual(200, response.status_code)
        self.assertURLEqual(
            self.white_mouse.website_url,
            response.url,
            'Customer should be redirected to the product page',
        )
        response = self.url_open(self.black_mouse_item['link'])
        self.assertEqual(200, response.status_code)
        self.assertURLEqual(
            self.black_mouse.website_url,
            response.url,
            'Customer should be redirected to the product page',
        )

    def test_gmc_product_prices(self):
        """Test links for different pricelists redirect to same price as on google shopping"""
        # case default pricelist
        self.update_items()
        self.assertEqual('79.0 USD', self.white_mouse_item['price'], 'Public User pricelist')
        self.assertEqual('99.0 USD', self.black_mouse_item['price'], 'Public User pricelist')
        # price in the data source must be equal to those at `link`
        self.start_tour(
            self.white_mouse_item['link'],
            'website_sale_gmc_check_advertised_prices_white_mouse_usd',
        )
        self.start_tour(
            self.black_mouse_item['link'],
            'website_sale_gmc_check_advertised_prices_black_mouse_usd',
        )
        # case with christmas pricelist
        self.update_items(context={'forced_pricelist': self.christmas_pricelist})
        # 79.0 (list_price) * 1.1 (EUR rate) - 10% (discount)
        self.assertEqual('78.21 EUR', self.white_mouse_item['sale_price'])
        # 99.0 (list_price) * 1.1 (EUR rate) - 10% (discount)
        self.assertEqual('98.01 EUR', self.black_mouse_item['sale_price'])
        # 129.0 (list_price) * 1.1 (EUR rate)
        self.assertEqual('141.9 EUR', self.items[self.keyboard]['price'])
        self.assertNotIn('sale_price', self.items[self.keyboard])  # no discount
        # price in the data source must be equal to those at `link`
        self.start_tour(
            self.white_mouse_item['link'],
            'website_sale_gmc_check_advertised_prices_white_mouse_christmas',
        )
        self.start_tour(
            self.black_mouse_item['link'],
            'website_sale_gmc_check_advertised_prices_black_mouse_christmas',
        )
        # case with 'Tax Included' in price option turned on
        self.website.show_line_subtotals_tax_selection = 'tax_included'
        self.update_items()
        self.assertEqual('90.85 USD', self.white_mouse_item['price'], '79.0 + 15% tax')
        self.assertEqual('113.85 USD', self.black_mouse_item['price'], '99.0 + 15% tax')
        self.start_tour(
            self.white_mouse_item['link'],
            'website_sale_gmc_check_advertised_prices_white_mouse_tax_included',
        )
        self.start_tour(
            self.black_mouse_item['link'],
            'website_sale_gmc_check_advertised_prices_black_mouse_tax_included',
        )

    def test_gmc_product_images(self):
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
            ],
        })
        self.white_mouse.write({
            'image_variant_1920': self.image_white_mouse,
        })
        self.black_mouse.write({
            'product_variant_image_ids': [
                Command.create({
                    'name': 'black_mouse_extra_image',
                    'image_1920': self.extra_image_black_mouse,
                })
            ]
        })
        self.update_items()
        self.assertIn('image_link', self.white_mouse_item, 'An `image_link` is required.')
        self.assertIn('image_link', self.black_mouse_item, 'An `image_link` is required.')
        self.assertEqual(
            1,
            len(self.white_mouse_item['additionnal_image_link']),
            'Since it inherits from the mouse template, it should have its extra image.',
        )
        self.assertEqual(
            2,
            len(self.black_mouse_item['additionnal_image_link']),
            'Since it inherits from the mouse template, it should have its extra image, plus the '
            'variant specific extra image.',
        )
        response = self.url_open(self.white_mouse_item['image_link'])
        response_image = base64.encodebytes(response.content).replace(b'\n', b'')
        self.assertEqual(
            response_image,
            self.image_white_mouse,
            'White mouse has a variant image, so it should be used.',
        )
        response = self.url_open(self.black_mouse_item['image_link'])
        response_image = base64.encodebytes(response.content).replace(b'\n', b'')
        self.assertEqual(
            response_image,
            self.image_template,
            'Black mouse does not have a variant image, should fall back to the template image.',
        )
        response = self.url_open(self.white_mouse_item['additionnal_image_link'][0])
        response_image = base64.encodebytes(response.content).replace(b'\n', b'')
        self.assertEqual(
            response_image,
            self.extra_image_template,
            'If the template has some extra image, and there is space left for additionnal images '
            '(limited to 5), then it should use them.',
        )
        response = self.url_open(self.black_mouse_item['additionnal_image_link'][0])
        response_image = base64.encodebytes(response.content).replace(b'\n', b'')
        self.assertEqual(
            response_image,
            self.extra_image_black_mouse,
            'Black mouse does have a variant extra image, so it should be first in the list.',
        )
        response = self.url_open(self.black_mouse_item['additionnal_image_link'][1])
        response_image = base64.encodebytes(response.content).replace(b'\n', b'')
        self.assertEqual(
            response_image,
            self.extra_image_template,
            'If the template has some extra image, and there is space left for additionnal images '
            '(limited to 5), then it should use them.',
        )

        self.black_mouse.write({
            'product_variant_image_ids': [
                Command.create({
                    'name': f'image {i}',
                    'image_1920': self.extra_image_black_mouse,
                })
                for i in range(9)  # add 9 more, total = 10 + template extra image = 11
            ]
        })
        self.update_items()
        self.assertEqual(
            10,
            len(self.black_mouse_item['additionnal_image_link']),
            'Google supports up to 10 additionnal images',
        )

    def test_gmc_product_identifier(self):
        self.update_items()
        self.assertEqual(
            self.white_mouse.barcode,
            self.white_mouse_item['gtin'],
            'If the product has a barcode, then it should be sent as `gtin`',
        )
        self.assertEqual(
            'yes',
            self.white_mouse_item['identifier_exists'],
            'White mouse does have an identifier, so it should be told to Google',
        )
        self.assertNotIn(
            'gtin',
            self.black_mouse_item,
            'Black mouse does not have any identifier, so it should be told to Google',
        )
        self.assertEqual(
            'no',
            self.black_mouse_item['identifier_exists'],
            'Black mouse does not have any identifier, so it should be specified to Google',
        )

    def test_gmc_product_type(self):
        # Electronics / Electronics Accessories / Computer Accessories
        # Electronics Accessories / Computer Components / Input Devices
        (
            elec_root,
            elec_acc_sub,
            computer_acc,
            elec_acc_root,
            computer_comp,
            input_devices,
        ) = self.env['product.public.category'].create([
            {'name': 'Electronics'},
            {'name': 'Electronics Accessories'},
            {'name': 'Computer Accessories', 'sequence': 2},
            {'name': 'Electronics Accessories'},
            {'name': 'Computer Components'},
            {'name': 'Input Devices', 'sequence': 1},
        ])
        computer_acc.parent_id = elec_acc_sub
        elec_acc_sub.parent_id = elec_root
        input_devices.parent_id = computer_comp
        computer_comp.parent_id = elec_acc_root
        self.public_categories = computer_acc + input_devices
        self.mouse_template.public_categ_ids = self.public_categories
        self.update_items()
        self.assertListEqual(
            list(
                name.replace('/', '>')
                for name in self.public_categories.sorted('sequence').mapped('display_name')
            ),
            self.white_mouse_item['product_type'],
            'Product type should follow the sequence order as the first in the list will have the '
            'most impact in Google algorithms',
        )
        self.mouse_template.write({
            'public_categ_ids': [
                Command.create({'name': f'Category {i}'}) for i in range(5)  # add 5 more, total = 7
            ]
        })
        self.update_items()
        self.assertEqual(
            5,
            len(self.white_mouse_item['product_type']),
            'Google supports up to 5 product type.',
        )

    def test_gmc_product_variants(self):
        some_attribute = self.env['product.attribute'].create([
            {
                'name': 'Color',
                'value_ids': [Command.create({'name': 'white', 'sequence': 1})],
            },
            {
                'name': 'Material',
                'value_ids': [Command.create({'name': 'wood', 'sequence': 1})],
            },
        ])
        product_no_variant = (
            self.env['product.template']
            .create({
                'name': 'Test product',
                'attribute_line_ids': [
                    Command.create({
                        'attribute_id': attr.id,
                        'value_ids': [Command.set(attr.value_ids.ids)],
                    })
                    for attr in some_attribute
                ],
                'list_price': 49.0,
            })
            .product_variant_ids
        )
        self.products |= product_no_variant
        self.update_items()
        self.assertEqual(
            self.white_mouse_item['item_group_id'],
            self.black_mouse_item['item_group_id'],
            'This white and black mouse are variants of the same product, therefore they should be '
            'linked.',
        )
        self.assertNotIn(
            'item_group_id',
            self.items[product_no_variant],
            'A product that has no variant, or only one with attributes, should not be linked to a '
            'group.',
        )

    def test_gmc_product_bundles(self):
        self.update_items()
        self.assertEqual(
            'yes',
            self.items[self.product_bundle]['is_bundle'],
            'Combo products should be considered as bundles in Google.',
        )
        self.assertEqual(
            'no',
            self.white_mouse_item['is_bundle'],
            'Consu products should not be considered as bundles in Google.',
        )

    def test_gmc_product_labels(self):
        tags = [f'tag {i}' for i in range(10)]
        self.mouse_template.write({
            'product_tag_ids': [
                Command.create({'name': tag, 'sequence': i}) for i, tag in enumerate(tags)
            ]
        })
        self.update_items()
        self.assertEqual(
            5,
            len(self.white_mouse_item['custom_label']),
            'Google only supports up to 5 custom labels',
        )
        self.assertListEqual(
            tags[:5],
            list(name for _, name in self.white_mouse_item['custom_label']),
            'Since we are limited, take the highest priority ones according to `sequence`',
        )

    def test_gmc_product_shipping(self):
        self.env['delivery.carrier'].search([]).action_archive()
        shipping_product = self.env['product.product'].create(
            {'name': 'Shipping', 'list_price': 14.99}
        )
        local_shipping_product = self.env['product.product'].create(
            {'name': 'Cheap Local Shipping', 'list_price': 2.99}
        )
        belgium = self.delivery_countries.search([('code', '=', 'BE')])
        self.env['delivery.carrier'].create([
            {
                'name': 'Local Shipping',
                'delivery_type': 'fixed',
                'country_ids': [Command.set(belgium.ids)],
                'product_id': local_shipping_product.id,
                'is_published': True,
            },
            {
                'name': 'Global Free above $100',
                'delivery_type': 'fixed',
                'country_ids': [Command.set(self.delivery_countries.ids)],
                'free_over': True,
                'amount': 100.0,
                'product_id': shipping_product.id,
                'is_published': True,
            },
            {
                'name': 'Local Free above $95',
                'delivery_type': 'fixed',
                'country_ids': [Command.set(belgium.ids)],
                'free_over': True,
                'amount': 95.0,
                'product_id': shipping_product.id,
                'max_weight': 20.0,
                'is_published': True,
            },
        ])
        self.products += self.env['product.product'].create({
            'name': 'Heavy product',
            'weight': 100.0,
        })
        heavy_product = self.products[-1]
        self.update_items()
        self.assertListEqual(
            ['2.99 USD', '14.99 USD', '14.99 USD'],
            [rate['price'] for rate in self.white_mouse_item['shipping']],
            'The best shipping in Belgium should be 2.99, since the Local option is available. '
            'Outside of Belgium it should be 14.99 for the white mouse since it does not get the '
            'free over $95.',
        )
        self.assertListEqual(
            ['0.0 USD', '0.0 USD', '0.0 USD'],
            [rate['price'] for rate in self.black_mouse_item['shipping']],
            'The best shipping for all the coutries should be free since black mouse price is '
            'above $100 (15% tax included).',
        )
        self.assertListEqual(
            ['95.0 USD', '95.0 USD'],
            [
                threshold['price_threshold']
                for threshold in (
                    self.white_mouse_item['free_shipping_threshold'][:1]
                    + self.black_mouse_item['free_shipping_threshold'][:1]
                )
            ],
            'In Belgium, the best free over rule is $95 for both the white and black mouses.',
        )
        self.assertListEqual(
            ['100.0 USD', '100.0 USD', '100.0 USD', '100.0 USD'],
            [
                threshold['price_threshold']
                for threshold in (
                    self.white_mouse_item['free_shipping_threshold'][1:]
                    + self.black_mouse_item['free_shipping_threshold'][1:]
                )
            ],
            'Outside of Belgium the best free over rule is $100 for both black and white mouses.',
        )
        self.assertListEqual(
            ['100.0 USD', '100.0 USD', '100.0 USD'],
            [
                threshold['price_threshold']
                for threshold in self.items[heavy_product]['free_shipping_threshold']
            ],
            'For the heavy product, the best free over rule is $100 in all countries, even'
            ' Belgium.',
        )

    def test_gmc_product_availability(self):
        self.update_items()
        self.assertEqual(
            'in_stock',
            self.white_mouse_item['availability'],
            'The availability should always be `in_stock`. (Could be overiden in'
            ' `website_sale_stock` module)',
        )

    def test_gmc_product_unit_pricing(self):
        self.env.user.write({
            'groups_id': [
                Command.link(self.env.ref('uom.group_uom').id),
            ],
        })
        uom_litre = self.env.ref('uom.product_uom_litre')
        base_unit_litre = self.env['website.base.unit'].create({'name': 'l'})
        six_pack = self.env['product.product'].create([{
            'name': 'Water Pack 6L',
            'list_price': 12.0,
            'uom_id': uom_litre.id,
            'base_unit_count': 6.0,
            'base_unit_id': base_unit_litre.id,
        }])
        self.products |= six_pack
        self.update_items()

        self.assertNotIn(
            'unit_pricing_measure',
            self.items[six_pack],
            'Product Reference Price is not enabled, so it should not be part of the feed.',
        )
        self.env.user.write({
            'groups_id': [
                Command.link(self.env.ref('website_sale.group_show_uom_price').id),
            ],
        })
        self.update_items()
        self.assertEqual('6l', self.items[six_pack]['unit_pricing_measure'], '$12 / 6l')

        six_pack.base_unit_id = False
        self.update_items()
        self.assertNotIn(
            'unit_pricing_measure', self.items[six_pack], '`L` is not a supported unit in GMC'
        )
