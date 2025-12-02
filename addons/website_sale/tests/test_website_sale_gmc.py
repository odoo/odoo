# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from lxml import etree
from urllib.parse import urlparse

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale.tests.common import MockRequest
from odoo.addons.website_sale.tests.common_gmc import WebsiteSaleGMCCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleGMC(WebsiteSaleGMCCommon, HttpCase):

    def test_gmc_xml_accessible_if_gmc_setting_enabled(self):
        response = self.url_open(self.gmc_feed.url)

        self.assertEqual(200, response.status_code)

    def test_gmc_xml_not_found_if_gmc_setting_disabled(self):
        self.website.enabled_gmc_src = False

        response = self.url_open(self.gmc_feed.url)

        self.assertEqual(404, response.status_code, 'Not Found')

    def test_gmc_xml_correct_xml_format(self):
        response = self.url_open(self.gmc_feed.url)

        gmc_xml = etree.XML(response.content)  # assert valid xml
        self.assertEqual(self.website.name, gmc_xml.xpath('//title')[0].text)
        self.assertURLEqual('/en', gmc_xml.xpath('//link')[0].text)
        self.assertEqual(
            'This is the homepage of the website',
            gmc_xml.xpath('//description')[0].text,
        )

    def test_gmc_xml_localization(self):
        fr_lang = self.env['res.lang']._activate_lang('fr_FR')
        self.website.language_ids += fr_lang
        self.gmc_feed.lang_id = fr_lang
        self.red_sofa.with_context(lang=fr_lang.code).name = 'Canapé'
        self.color_attribute_red.with_context(lang=fr_lang.code).name = 'rouge'

        self.update_items()

        self.assertRegex(
            self.parse_http_location(self.red_sofa_item['link']).path,
            f'^\\/{fr_lang.url_code}.*',
            'The links must redirect to the french website.',
        )
        self.assertEqual(
            'Canapé (rouge)',
            self.red_sofa_item['title'],
        )

    def test_gmc_xml_pricelist(self):
        self.gmc_feed.pricelist_id = self.eur_pricelist

        with MockRequest(
            self.env,
            website=self.website,
            website_sale_current_pl=self.pricelist.id,
        ):
            gmc_xml = etree.XML(self.gmc_feed._render_gmc_feed().encode())

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
                },
                item.keys(),
            )  # subseteq

    def test_gmc_items_use_internal_reference_if_exists(self):
        """Test prefer internal code to database id"""
        # setup: red_sofa.code = 'SOFA-R', blue_sofa.code = False
        self.update_items()

        self.assertEqual(self.red_sofa.code, self.red_sofa_item['id'])
        self.assertEqual(self.blue_sofa.id, self.blue_sofa_item['id'])

    def test_gmc_items_link_redirects_to_correct_product_case_default_pricelist(self):
        self.update_items()

        for product in self.red_sofa + self.blue_sofa:
            response = self.url_open(self.items[product]['link'])

            self.assertEqual(200, response.status_code)
            self.assertURLEqual(product.website_url, response.url)

    def test_gmc_items_link_redirects_to_correct_product_case_specific_pricelist(self):
        self.gmc_feed.pricelist_id = self.eur_pricelist
        self.update_items()

        for product in self.red_sofa + self.blue_sofa:
            response = self.url_open(self.items[product]['link'])

            self.assertEqual(200, response.status_code)
            url = urlparse(product.website_url)
            self.assertURLEqual(
                f'{url.path}'
                 f'?attribute_values={",".join(str(i) for i in product.product_template_attribute_value_ids.product_attribute_value_id.ids)}'
                 f'&pricelist={self.eur_pricelist.id}'
                 f'#{url.fragment}',
                response.url,
            )

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
        self.gmc_feed.pricelist_id = self._create_pricelist(
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

        self.update_items()

        # 1000.0 (list_price) * 1.1 (EUR rate) - 10% (discount)
        self.assertEqual('990.0 EUR', self.red_sofa_item['sale_price'])
        # 1200.0 (list_price) * 1.1 (EUR rate) - 10% (discount)
        self.assertEqual('1188.0 EUR', self.blue_sofa_item['sale_price'])
        # 100.0 (list_price) * 1.1 (EUR rate)
        self.assertEqual('110.0 EUR', self.items[self.blanket]['price'])
        self.assertNotIn('sale_price', self.items[self.blanket])  # no discount
        self.assertNotEqual(self.red_sofa_item['link'], self.blue_sofa_item['link'])
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

    def test_gmc_items_additional_images_limit_to_10(self):
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

        self.assertEqual(10, len(self.blue_sofa_item['additional_image_link']))

    def test_gmc_items_identifier_exists_iff_barcode_exists(self):
        self.red_sofa.barcode = '0232344532564'

        self.update_items()

        self.assertEqual(self.red_sofa.barcode, self.red_sofa_item['gtin'])
        self.assertEqual('yes', self.red_sofa_item['identifier_exists'])
        self.assertNotIn('gtin', self.blue_sofa_item)
        self.assertEqual('no', self.blue_sofa_item['identifier_exists'])

    def test_gmc_items_sorted_types(self):
        # Furnitures / Sofas
        # Furnitures / Indoor Furnitures / Indoor Sofas
        furnitures_categ, sofas_categ = self._create_public_category([
            {'name': 'Furnitures'},
            {'name': 'Sofas', 'sequence': 1},
        ])
        indoor_sofas_categ = self._create_public_category([
            {'name': 'Indoor Furnitures', 'parent_id': furnitures_categ.id},
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
            'is_published': True,
        }).product_variant_ids
        self.products |= product_one_variant

        self.update_items()

        # same template
        self.assertEqual(self.red_sofa_item['item_group_id'], self.blue_sofa_item['item_group_id'])
        # no other variant
        self.assertNotIn('item_group_id', self.items[product_one_variant])

    def test_gmc_items_bundle_if_is_combo_product(self):
        self.update_items()

        self.assertEqual('yes', self.items[self.sofa_bundle]['is_bundle'])
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

        self.assertListEqual(tags, [name for _, name in self.red_sofa_item['custom_label']])

    def test_gmc_items_tags_limit_to_5(self):
        self.product_template_sofa.write({
            'product_tag_ids': [
                Command.create({'name': f"Tag {i}", 'sequence': i})
                for i in range(10)
            ]
        })

        self.update_items()

        self.assertEqual(5, len(self.red_sofa_item['custom_label']))

    def test_gmc_items_default_availability_in_stock(self):
        self.update_items()

        self.assertEqual(
            'in_stock',
            self.red_sofa_item['availability'],
        )

    def _setup_6l_water_pack(self):
        self.env.user.group_ids |= self.env.ref('uom.group_uom')
        uom_litre = self.env.ref('uom.product_uom_pack_6')
        base_unit_litre = self.env['website.base.unit'].create({'name': 'L'})
        six_pack = self.env['product.product'].create([{
            'name': 'Water Pack 6L',
            'list_price': 12.0,
            'uom_id': uom_litre.id,
            'base_unit_count': 6.0,
            'base_unit_id': base_unit_litre.id,
            'is_published': True,
        }])
        self.products |= six_pack
        return six_pack

    def test_gmc_items_unit_pricing_iff_product_reference_enabled(self):
        six_pack = self._setup_6l_water_pack()
        self.update_items()
        self.assertNotIn('unit_pricing_measure', self.items[six_pack])

        # enable "Product Reference Price" setting
        self.env.user.group_ids |= self.env.ref('website_sale.group_show_uom_price')
        self.update_items()

        self.assertEqual('6.0l', self.items[six_pack]['unit_pricing_measure'], '$12 / 6l')

    def test_gmc_items_dont_send_unsupported_unit(self):
        six_pack = self._setup_6l_water_pack()
        six_pack.base_unit_id = False  # remove `L` alias -> falls back to `Pack of 6`

        self.update_items()

        self.assertNotIn('unit_pricing_measure', self.items[six_pack])
