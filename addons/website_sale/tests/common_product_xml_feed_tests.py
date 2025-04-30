# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from lxml import etree
from werkzeug.exceptions import NotFound
from urllib.parse import urlparse

from odoo import Command
from odoo.tests import HttpCase

from odoo.addons.website_sale.tests.common import MockRequest
from odoo.addons.website_sale.tests.website_sale_feed_common import WebsiteSaleFeedCommon


class CommonProductFeedXmlFeed(WebsiteSaleFeedCommon, HttpCase):

    def test_xml_accessible_if_setting_enabled(self, response):
        self.assertEqual(200, response.status_code)

    def test_xml_not_found_if_setting_disabled(self, feed_type):

        with self.assertRaises(NotFound), MockRequest(
            self.env,
            website=self.website,
            website_sale_current_pl=self.pricelist.id,
        ):
            if feed_type == "gmc":
                self.website.enabled_gmc_src = False
                self.WebsiteSaleFeedController.gmc_feed()
            elif feed_type == "meta":
                self.website.enabled_meta_src = False
                self.WebsiteSaleFeedController.meta_feed()
            else:
                raise ValueError(f"Unsupported feed_type: {feed_type}")

    def test_correct_xml_format(self, response):
        feed_xml = etree.XML(response.content)  # assert valid xml
        self.assertEqual(self.website.name, feed_xml.xpath('//title')[0].text)
        self.assertURLEqual('/', feed_xml.xpath('//link')[0].text)
        self.assertEqual(
            'This is the homepage of the website',
            feed_xml.xpath('//description')[0].text,
        )

    def test_xml_localization(self):
        fr_lang = self.env['res.lang']._activate_lang('fr_FR')
        self.website.language_ids += fr_lang
        self.red_sofa.with_context(lang=fr_lang.code).name = 'Canapé'
        self.color_attribute_red.with_context(lang=fr_lang.code).name = 'rouge'

        self.update_items(lang=fr_lang.code)

        self.assertRegex(
            self.parse_http_location(self.red_sofa_item['link']).path,
            f'^\\/{fr_lang.url_code}.*',
            'The links must redirect to the french website.',
        )
        self.assertEqual(
            'Canapé (rouge)',
            self.red_sofa_item['title'],
        )

    def test_feed_items_use_internal_reference_if_exists(self):
        """Test prefer internal code to database id"""
        # setup: red_sofa.code = 'SOFA-R', blue_sofa.code = False
        self.update_items()

        self.assertEqual(self.red_sofa.code, self.red_sofa_item['id'])
        self.assertEqual(self.blue_sofa.id, self.blue_sofa_item['id'])

    def test_feed_items_link_redirects_to_correct_product(self):
        self.update_items()

        for product in self.red_sofa + self.blue_sofa:
            response = self.url_open(self.items[product]['link'])

            self.assertEqual(200, response.status_code)
            url = urlparse(product.website_url)
            self.assertURLEqual(
                f'{url.path}?pricelist={self.pricelist.id}#{url.fragment}',
                response.url,
            )

    def test_feed_items_prices_match_website_prices_default(self):
        self.update_items()

        self.assertEqual('1000.0 USD', self.red_sofa_item['price'])
        self.assertEqual('1200.0 USD', self.blue_sofa_item['price'])
        self.start_tour(
            self.red_sofa_item['link'],
            'website_sale_product_feed_check_advertised_prices_red_sofa_default',
        )
        self.start_tour(
            self.blue_sofa_item['link'],
            'website_sale_product_feed_check_advertised_prices_blue_sofa_default',
        )

    def test_feed_items_prices_match_website_prices_christmas(self):
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

        self.update_items(pricelist=self.christmas_pricelist)

        # 1000.0 (list_price) * 1.1 (EUR rate) - 10% (discount)
        self.assertEqual('990.0 EUR', self.red_sofa_item['sale_price'])
        # 1200.0 (list_price) * 1.1 (EUR rate) - 10% (discount)
        self.assertEqual('1188.0 EUR', self.blue_sofa_item['sale_price'])
        # 100.0 (list_price) * 1.1 (EUR rate)
        self.assertEqual('110.0 EUR', self.items[self.blanket]['price'])
        self.assertNotIn('sale_price', self.items[self.blanket])  # no discount
        self.start_tour(
            self.red_sofa_item['link'],
            'website_sale_product_feed_check_advertised_prices_red_sofa_christmas',
        )
        self.start_tour(
            self.blue_sofa_item['link'],
            'website_sale_product_feed_check_advertised_prices_blue_sofa_christmas',
        )

    def test_feed_items_prices_match_website_prices_tax_included(self):
        # 15% taxes
        self.website.show_line_subtotals_tax_selection = 'tax_included'

        self.update_items()

        self.assertEqual('1150.0 USD', self.red_sofa_item['price'])
        self.assertEqual('1380.0 USD', self.blue_sofa_item['price'])
        self.start_tour(
            self.red_sofa_item['link'],
            'website_sale_product_feed_check_advertised_prices_red_sofa_tax_included',
        )
        self.start_tour(
            self.blue_sofa_item['link'],
            'website_sale_product_feed_check_advertised_prices_blue_sofa_tax_included',
        )

    def test_feed_items_additional_images_limit_to_10(self):
        image = self._create_image('blue')
        self.blue_sofa.write({
            'product_variant_image_ids': [
                Command.create({
                    'name': f'image {i}',
                    'image_1920': image,
                })
                for i in range(12)
            ],
        })

        self.update_items()

        self.assertEqual(10, len(self.blue_sofa_item['additional_image_link']))

    def test_feed_items_sorted_types(self):
        # Furnitures / Sofas
        # Furnitures / Indoor Furnitures / Indoor Sofas
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
            [
                name.replace('/', '>')
                for name in self.public_categories.sorted('sequence').mapped('display_name')
            ],
            self.red_sofa_item['product_type'],
        )

    def test_feed_items_types_limit_to_5(self):
        self.product_template_sofa.write({
            'public_categ_ids': [
                Command.create({'name': f'Category {i}'}) for i in range(6)
            ],
        })

        self.update_items()

        self.assertEqual(5, len(self.red_sofa_item['product_type']))

    def test_feed_product_variants(self):
        product_one_variant = self.env['product.template'].create({
            'name': 'Test product',
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attr.attribute_id.id,
                    'value_ids': [Command.link(attr.id)],
                })
                for attr in (self.color_attribute_green + self.size_attribute_l)
            ],
            'list_price': 49.0,
        }).product_variant_ids
        self.products |= product_one_variant

        self.update_items()

        # same template
        self.assertEqual(self.red_sofa_item['item_group_id'], self.blue_sofa_item['item_group_id'])
        # no other variant
        self.assertNotIn('item_group_id', self.items[product_one_variant])

    def test_feed_product_detail(self):
        color_attr = self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].create({'name': 'Size'})
        red = self.env['product.attribute.value'].create({'name': 'Red', 'attribute_id': color_attr.id})
        xl = self.env['product.attribute.value'].create({'name': 'XL', 'attribute_id': size_attr.id})

        product = self._create_variant_product("Test Shirt", [(color_attr, red), (size_attr, xl)])
        self.products += product

        self.update_items()

        expected_details = [('Color', 'Red'), ('Size', 'XL')]
        self.assertListEqual(
            self.items[product]['product_detail'],
            expected_details,
        )

    def test_all_product_xml_feed(self):
        response = self.url_open(self.feed_url)
        feed_type = self.feed_type
        self.test_xml_accessible_if_setting_enabled(response)
        self.test_xml_not_found_if_setting_disabled(feed_type)
        self.test_correct_xml_format(response)
        self.test_xml_localization()
        self.test_feed_items_use_internal_reference_if_exists()
        self.test_feed_items_link_redirects_to_correct_product()
        self.test_feed_items_prices_match_website_prices_default()
        self.test_feed_items_prices_match_website_prices_christmas()
        self.test_feed_items_prices_match_website_prices_tax_included()
        self.test_feed_items_additional_images_limit_to_10()
        self.test_feed_items_sorted_types()
        self.test_feed_items_types_limit_to_5()
        self.test_feed_product_variants()
        self.test_feed_product_detail()
