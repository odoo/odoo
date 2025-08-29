# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import Command
from odoo.tests import tagged

from odoo.addons.website_sale.tests.website_sale_feed_common import WebsiteSaleFeedCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleGMC(WebsiteSaleFeedCommon):

    def setUp(self):
        super().setUp()
        self.website.enabled_gmc_src = True
        self.feed_type = 'gmc'
        self.feed_url = '/gmc.xml'
        self.enabled_flag_name = 'enabled_gmc_src'

    def test_all_gmc_product_xml_feed(self):
        super().test_all_product_xml_feed()

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

    def test_01_gmc_items_best_shipping_rate_per_country(self):
        self._prepare_carrier(
            self._prepare_carrier_product(list_price=2.99),
            name="Local Shipping",
            country_ids=[Command.set(self.country_be.ids)],
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
            country_ids=[Command.set(self.country_be.ids)],
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
            country_ids=[Command.set(self.country_be.ids)],
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
        self.env.user.group_ids |= self.env.ref('uom.group_uom')
        uom_litre = self.env.ref('uom.product_uom_pack_6')
        base_unit_litre = self.env['website.base.unit'].create({'name': 'L'})
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
        self.env.user.group_ids |= self.env.ref('website_sale.group_show_uom_price')
        self.update_items()

        self.assertEqual('6.0l', self.items[six_pack]['unit_pricing_measure'], '$12 / 6l')

    def test_gmc_items_dont_send_unsupported_unit(self):
        six_pack = self._setup_6l_water_pack()
        six_pack.base_unit_id = False  # remove `L` alias -> falls back to `Pack of 6`

        self.update_items()

        self.assertNotIn('unit_pricing_measure', self.items[six_pack])
