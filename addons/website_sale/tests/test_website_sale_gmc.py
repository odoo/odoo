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

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website.tools import MockRequest
from odoo.addons.delivery.tests.common import DeliveryCommon
from odoo.addons.product.tests.common import ProductVariantsCommon


class WebsiteSaleGMCCommon(ProductVariantsCommon, DeliveryCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.public_user = cls.env.ref('base.public_user')
        cls.website = cls.env['website'].browse(1)
        cls.website.enabled_gmc_src = True

        cls.product_template_sofa.list_price = 1000.0
        cls.color_attribute_red.default_extra_price = 200.0
        (
            cls.red_sofa,
            cls.blue_sofa,
        ) = cls.product_template_sofa.product_variant_ids[:2]
        cls.red_sofa.default_code = 'SOFA-R'
        (
            cls.blue_sofa
            .product_template_attribute_value_ids
            .filtered(lambda v: v.name == 'blue')
        ).price_extra = 200.0
        cls.blanket = cls._create_product(name="Blanket")
        combos = cls.env['product.combo'].create([
            {
                'name': "Sofa Combo",
                'combo_item_ids': [
                    Command.create({'product_id': cls.red_sofa.id}),
                    Command.create({'product_id': cls.blue_sofa.id})
                ]
            },
            {
                'name': "Blanket Combo",
                'combo_item_ids': [
                    Command.create({'product_id': cls.blanket.id}),
                ]
            }
        ])
        cls.product_bundle = cls._create_product(
            name="Sofa + Blanket",
            type='combo',
            combo_ids=[Command.set(combos.ids)],
            list_price=1099.0
        )
        cls.products = cls.red_sofa + cls.blue_sofa + cls.blanket + cls.product_bundle
        cls.products.website_published = True
        cls.eur_currency = cls.env.ref('base.EUR')
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
        cls.delivery_countries = cls.env['res.country'].search([('code', 'in', ('BE', 'LU', 'GB'))])
        cls.belgium = cls.delivery_countries.search([('code', '=', 'BE')])
        cls.carrier.write({
            'country_ids': [Command.set(cls.delivery_countries.ids)],  # limit computation overhead
            'free_over': True,
            'amount': 1200.0,
            'website_published': True,
        })
        cls.carrier.product_id.list_price = 5.0
        cls.WebsiteSaleController = WebsiteSale()

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
        self.red_sofa_item = self.items[self.red_sofa]
        self.blue_sofa_item = self.items[self.blue_sofa]

@tagged('post_install', '-at_install')
class TestWebsiteSaleGMC(WebsiteSaleGMCCommon, HttpCase):

    def test_gmc_xml_accessible_iff_gmc_src_enabled(self):
        self.website.enabled_gmc_src = False
        with self.assertRaises(NotFound), self.mock_public_request():
            self.WebsiteSaleController.gmc_data_source()

        self.website.enabled_gmc_src = True
        response = self.url_open('/gmc.xml')

        self.assertEqual(200, response.status_code)
        gmc_xml = etree.XML(response.content)  # valid xml
        self.assertEqual(f'Home | {self.website.name}', gmc_xml.xpath('//title')[0].text)
        self.assertURLEqual('/', gmc_xml.xpath('//link')[0].text)
        self.assertEqual(
            'This is the homepage of the website',
            gmc_xml.xpath('//description')[0].text,
        )

    def test_gmc_xml_translation(self):
        fr_lang = self.env['res.lang']._activate_lang('fr_FR')
        self.website.language_ids += fr_lang
        self.website.name = 'The best website'
        self.website.with_context(lang=fr_lang.code).name = 'Mon unique site'
        self.red_sofa.with_context(lang=fr_lang.code).name = 'Canapé'
        self.color_attribute_red.with_context(lang=fr_lang.code).name = 'rouge'

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
            'Canapé (rouge)',
            gmc_xml.xpath(
                '//item[g:id="SOFA-R"]/g:title', namespaces={'g': 'http://base.google.com/ns/1.0'}
            )[0].text,
        )

    def test_gmc_xml_pricelist(self):
        self._create_pricelist(
            name="EUR",
            currency_id=self.eur_currency.id,
            selectable=True,
        )
        response = self.url_open('/gmc-eur.xml')
        self.assertEqual(200, response.status_code)
        gmc_xml = etree.XML(response.content)
        self.assertEqual(
            '1100.0 EUR',  # 1000.0 * 1.1 (EUR rate)
            gmc_xml.xpath(
                '//item[g:id="SOFA-R"]/g:price', namespaces={'g': 'http://base.google.com/ns/1.0'}
            )[0].text
        )

    def test_gmc_items_required_fields(self):
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
            )  # subseteq

    def test_gmc_items_ignore_services(self):
        self.products += self._create_product(
            name="Service Type Product",
            type='service',
        )
        *consu_combo, service_product = self.products

        self.update_items()

        self.assertNotIn(service_product, self.items)
        self.assertGreaterEqual(set(consu_combo), self.items.keys())  # subseteq

    def test_gmc_items_use_internal_reference_if_exists(self):
        """Test prefer internal code to database id"""
        # setup: red_sofa.code = 'SOFA-R', blue_sofa.code = False
        self.update_items()

        self.assertEqual(self.red_sofa.code, self.red_sofa_item['id'])
        self.assertEqual(self.blue_sofa.id, self.blue_sofa_item['id'])

    def test_01_gmc_items_link_redirects_to_correct_product(self):
        self.update_items()

        response = self.url_open(self.red_sofa_item['link'])

        self.assertEqual(200, response.status_code)
        self.assertURLEqual(self.red_sofa.website_url, response.url)

    def test_02_gmc_items_link_redirects_to_correct_product(self):
        self.update_items()

        response = self.url_open(self.blue_sofa_item['link'])

        self.assertEqual(200, response.status_code)
        self.assertURLEqual(self.blue_sofa.website_url, response.url)

    def test_gmc_items_prices_match_website_prices_default(self):
        self.update_items()

        self.assertEqual('1000.0 USD', self.red_sofa_item['price'])
        self.assertEqual('1200.0 USD', self.blue_sofa_item['price'])
        self.start_tour(
            self.red_sofa_item['link'],
            'website_sale_gmc_check_advertised_prices_red_sofa_default',
        )
        self.start_tour(
            self.blue_sofa_item['link'],
            'website_sale_gmc_check_advertised_prices_blue_sofa_default',
        )

    def test_gmc_items_prices_match_website_prices_christmas(self):
        self.christmas_pricelist = self._create_pricelist(
            name="EUR Christmas Sales",
            currency_id=self.eur_currency.id,
            selectable=True,
            item_ids=[
                Command.create({
                    'product_tmpl_id': self.product_template_sofa.id,
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
        )

        self.update_items(context={'forced_pricelist': self.christmas_pricelist})

        # 1000.0 (list_price) * 1.1 (EUR rate) - 10% (discount)
        self.assertEqual('990.0 EUR', self.red_sofa_item['sale_price'])
        # 1200.0 (list_price) * 1.1 (EUR rate) - 10% (discount)
        self.assertEqual('1188.0 EUR', self.blue_sofa_item['sale_price'])
        # 100.0 (list_price) * 1.1 (EUR rate)
        self.assertEqual('110.0 EUR', self.items[self.blanket]['price'])
        self.assertNotIn('sale_price', self.items[self.blanket])  # no discount
        self.start_tour(
            self.red_sofa_item['link'],
            'website_sale_gmc_check_advertised_prices_red_sofa_christmas',
        )
        self.start_tour(
            self.blue_sofa_item['link'],
            'website_sale_gmc_check_advertised_prices_blue_sofa_christmas',
        )

    def test_gmc_items_prices_match_website_prices_tax_included(self):
        # 15% taxes
        self.website.show_line_subtotals_tax_selection = 'tax_included'

        self.update_items()

        self.assertEqual('1150.0 USD', self.red_sofa_item['price'])
        self.assertEqual('1380.0 USD', self.blue_sofa_item['price'])
        self.start_tour(
            self.red_sofa_item['link'],
            'website_sale_gmc_check_advertised_prices_red_sofa_tax_included',
        )
        self.start_tour(
            self.blue_sofa_item['link'],
            'website_sale_gmc_check_advertised_prices_blue_sofa_tax_included',
        )

    def _create_image(self, color):
        f = io.BytesIO()
        Image.new('RGB', (1920, 1080), color).save(f, 'JPEG')
        f.seek(0)
        return base64.b64encode(f.read())

    def url_open_image(self, link):
        response = self.url_open(link)
        return base64.encodebytes(response.content).replace(b'\n', b'')

    def test_gmc_items_images(self):
        image_template = self._create_image('green')
        image_red_sofa = self._create_image('red')
        self.product_template_sofa.image_1920 = image_template
        self.red_sofa.image_variant_1920 = image_red_sofa

        self.update_items()
        response_image_red_sofa = self.url_open_image(self.red_sofa_item['image_link'])
        response_image_blue_sofa = self.url_open_image(self.blue_sofa_item['image_link'])

        self.assertEqual(response_image_red_sofa, image_red_sofa)
        # no variant specific -> fallback to template
        self.assertEqual(response_image_blue_sofa, image_template)

    def test_gmc_items_additionnal_images(self):
        extra_image_template = self._create_image('white')
        extra_image_blue_sofa = self._create_image('blue')
        self.product_template_sofa.write({
            'product_template_image_ids': [Command.create({
                'name': 'extra_image',
                'image_1920': extra_image_template,
            })],
        })
        self.blue_sofa.write({
            'product_variant_image_ids': [Command.create({
                'name': 'black_mouse_extra_image',
                'image_1920': extra_image_blue_sofa,
            })],
        })

        self.update_items()
        response_image_red_sofa = self.url_open_image(self.red_sofa_item['additionnal_image_link'][0])
        response_image_blue_sofa_0 = self.url_open_image(self.blue_sofa_item['additionnal_image_link'][0])
        response_image_blue_sofa_1 = self.url_open_image(self.blue_sofa_item['additionnal_image_link'][1])

        self.assertEqual(1, len(self.red_sofa_item['additionnal_image_link']))  # template image
        # template image + variant image
        self.assertEqual(2, len(self.blue_sofa_item['additionnal_image_link']))
        self.assertEqual(response_image_red_sofa, extra_image_template)
        self.assertEqual(response_image_blue_sofa_0, extra_image_blue_sofa)
        self.assertEqual(response_image_blue_sofa_1, extra_image_template)

    def test_gmc_items_additionnal_images_limit_to_10(self):
        image = self._create_image('blue')
        self.blue_sofa.write({
            'product_variant_image_ids': [
                Command.create({
                    'name': f'image {i}',
                    'image_1920': image,
                })
                for i in range(12)
            ]
        })

        self.update_items()

        self.assertEqual(10, len(self.blue_sofa_item['additionnal_image_link']))

    def test_gmc_items_identifier_exists_iff_barcode_exists(self):
        self.red_sofa.barcode = '0232344532564'

        self.update_items()

        self.assertEqual(self.red_sofa.barcode, self.red_sofa_item['gtin'])
        self.assertEqual('yes', self.red_sofa_item['identifier_exists'])
        self.assertNotIn('gtin', self.blue_sofa_item)
        self.assertEqual('no', self.blue_sofa_item['identifier_exists'])

    def _create_public_category(self, list_vals):
        categs = self.env['product.public.category'].create(list_vals)
        for i in range(0, len(categs) - 1):
            categs[i].parent_id = categs[i + 1]
        return categs[-1]

    def test_gmc_items_sorted_types(self):
        # Furnitures / Sofas
        # Electronics / Electronics Accessories / Computer Accessories
        sofas_categ = self._create_public_category([
            {'name': 'Furnitures'},
            {'name': 'Sofas', 'sequence': 1},
        ])
        indoor_sofas_categ = self._create_public_category([
            {'name': 'Furnitures'},
            {'name': 'Indoor Furnitures'},
            {'name': 'Indoor Sofas', 'sequence': 2},
        ])
        self.public_categories = sofas_categ + indoor_sofas_categ
        self.product_template_sofa.public_categ_ids = self.public_categories

        self.update_items()

        self.assertListEqual(
            list(
                name.replace('/', '>')
                for name in self.public_categories.sorted('sequence').mapped('display_name')
            ),
            self.red_sofa_item['product_type']
        )

    def test_gmc_items_types_limit_to_5(self):
        self.product_template_sofa.write({
            'public_categ_ids': [
                Command.create({'name': f'Category {i}'}) for i in range(6)
            ]
        })

        self.update_items()

        self.assertEqual(5, len(self.red_sofa_item['product_type']))

    def test_gmc_product_variants(self):
        product_one_variant = (
            self.env['product.template']
            .create({
                'name': 'Test product',
                'attribute_line_ids': [
                    Command.create({
                        'attribute_id': attr.attribute_id.id,
                        'value_ids': [Command.link(attr.id)],
                    })
                    for attr in (self.color_attribute_green + self.size_attribute_l)
                ],
                'list_price': 49.0,
            })
            .product_variant_ids
        )
        self.products |= product_one_variant

        self.update_items()

        # same template
        self.assertEqual(self.red_sofa_item['item_group_id'], self.blue_sofa_item['item_group_id'])
        # no other variant
        self.assertNotIn('item_group_id', self.items[product_one_variant])

    def test_gmc_items_bundle_iff_combo(self):
        self.update_items()

        self.assertEqual('yes', self.items[self.product_bundle]['is_bundle'])
        self.assertEqual('no', self.red_sofa_item['is_bundle'])

    def test_gmc_items_sorted_labels(self):
        tags = [f'tag {i}' for i in range(3)]
        self.product_template_sofa.write({
            'product_tag_ids': [
                Command.create({'name': tag, 'sequence': i})
                for i, tag in enumerate(tags)
            ]
        })

        self.update_items()

        self.assertListEqual(
            tags,
            list(name for _, name in self.red_sofa_item['custom_label']),
        )

    def test_gmc_items_tags_limit_to_5(self):
        self.product_template_sofa.write({
            'product_tag_ids': [
                Command.create({'name': f"Tag {i}", 'sequence': i})
                for i in range(10)
            ]
        })

        self.update_items()

        self.assertEqual(5, len(self.red_sofa_item['custom_label']))

    def test_01_gmc_items_best_shipping_rate_per_country(self):
        self._prepare_carrier(
            self._prepare_carrier_product(list_price=2.99),
            name="Local Shipping",
            country_ids=[Command.set(self.belgium.ids)],
            website_published=True,
            fixed_price=2.99,
        )

        self.update_items()

        # Red sofa only gets a reduced delivery for Belgium
        self.assertDictEqual(
            {rate['country']: rate['price'] for rate in self.red_sofa_item['shipping']},
            {'BE': '2.99 USD', 'LU': '5.0 USD', 'GB': '5.0 USD'},
        )
        # Blue sofa price is $1200 -> free over
        self.assertDictEqual(
            {rate['country']: rate['price'] for rate in self.blue_sofa_item['shipping']},
            {'BE': '0.0 USD', 'LU': '0.0 USD', 'GB': '0.0 USD'},
        )

    def test_02_gmc_items_best_shipping_rate_per_country(self):
        self._prepare_carrier(
            self._prepare_carrier_product(list_price=2.99),
            name="Local Free above $100",
            country_ids=[Command.set(self.belgium.ids)],
            free_over=True,
            amount=100.0,
            max_weight=20.0,
            website_published=True,
        )
        heavy_product = self._create_product(name="Heavy product", weight=100.0)
        self.products += heavy_product

        self.update_items()

        # Free over in Belgium
        self.assertDictEqual(
            {rate['country']: rate['price'] for rate in self.red_sofa_item['shipping']},
            {'BE': '0.0 USD', 'LU': '5.0 USD', 'GB': '5.0 USD'},
        )
        # Too heavy for free over in Belgium
        self.assertDictEqual(
            {rate['country']: rate['price'] for rate in self.items[heavy_product]['shipping']},
            {'BE': '5.0 USD', 'LU': '5.0 USD', 'GB': '5.0 USD'},
        )

    def test_gmc_items_best_free_shipping_threshold(self):
        self._prepare_carrier(
            self._prepare_carrier_product(list_price=10.0),
            name="Local Carrier",
            country_ids=[Command.set(self.belgium.ids)],
            free_over=True,
            amount=100.0,
            website_published=True,
        )

        self.update_items()

        # In Belgium
        self.assertListEqual(
            ['100.0 USD', '100.0 USD'],
            [
                threshold['price_threshold']
                for threshold in (
                    self.red_sofa_item['free_shipping_threshold'][:1]
                    + self.blue_sofa_item['free_shipping_threshold'][:1]
                )
            ],
        )
        # Outside Belgium
        self.assertListEqual(
            ['1200.0 USD', '1200.0 USD', '1200.0 USD', '1200.0 USD'],
            [
                threshold['price_threshold']
                for threshold in (
                    self.red_sofa_item['free_shipping_threshold'][1:]
                    + self.blue_sofa_item['free_shipping_threshold'][1:]
                )
            ],
        )

    def test_gmc_items_default_availability_in_stock(self):
        self.update_items()

        self.assertEqual(
            'in_stock',
            self.red_sofa_item['availability'],
        )

    def _setup_6l_water_pack(self):
        self.env.user.groups_id |= self.env.ref('uom.group_uom')
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
        return six_pack

    def test_gmc_items_unit_pricing_iff_product_reference_enabled(self):
        six_pack = self._setup_6l_water_pack()
        self.update_items()
        self.assertNotIn('unit_pricing_measure', self.items[six_pack])

        # enable "Product Reference Price" setting
        self.env.user.groups_id |= self.env.ref('website_sale.group_show_uom_price')
        self.update_items()

        self.assertEqual('6l', self.items[six_pack]['unit_pricing_measure'], '$12 / 6l')

    def test_gmc_items_dont_send_unsupported_unit(self):
        six_pack = self._setup_6l_water_pack()
        six_pack.base_unit_id = False  # remove `l` alias -> falls back to `L`

        self.update_items()

        self.assertNotIn('unit_pricing_measure', self.items[six_pack])
