# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import Command
from odoo.tests import tagged

from odoo.addons.website_sale.tests.website_sale_feed_common import WebsiteSaleFeedCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleMeta(WebsiteSaleFeedCommon):

    def setUp(self):
        super().setUp()
        self.website.enabled_meta_src = True
        self.feed_type = 'meta'
        self.feed_url = '/meta.xml'
        self.enabled_flag_name = 'enabled_meta_src'

    def test_all_meta_product_xml_feed(self):
        super().test_all_product_xml_feed()

    def test_meta_xml_pricelist(self):
        self._create_pricelist(
            name="EUR",
            currency_id=self.eur_currency.id,
            selectable=True,
        )
        response = self.url_open('/meta-eur.xml')
        self.assertEqual(200, response.status_code)
        meta_xml = etree.XML(response.content)
        self.assertEqual(
            '1100.0 EUR',  # 1000.0 * 1.1 (EUR rate)
            meta_xml.xpath(
                '//item[g:id="SOFA-R"]/g:price', namespaces={'g': 'http://base.google.com/ns/1.0'},
            )[0].text,
        )

    def test_meta_items_required_fields(self):
        self.update_items()

        for item in self.items.values():
            self.assertLessEqual(
                {
                    'id',
                    'title',
                    'description',
                    'availability',
                    'price',
                    'link',
                    'image_link',
                },
                item.keys(),
            )  # subseteq

    def test_meta_items_internal_labels(self):
        tags = [f'tag {i}' for i in range(3)]
        self.product_template_sofa.write({
            'product_tag_ids': [
                Command.create({'name': tag, 'sequence': i})
                for i, tag in enumerate(tags)
            ],
        })
        expected_tags = [tag.lower().strip().replace(' ', '_') for tag in tags]
        self.update_items()
        self.assertListEqual(expected_tags, self.red_sofa_item['internal_label'])

    def test_meta_items_default_availability_in_stock(self):
        self.update_items()

        self.assertEqual(
            'in stock',
            self.red_sofa_item['availability'],
        )

    def test_01_meta_shipping_rate_with_region(self):
        self.env['delivery.carrier'].search([]).write({'website_published': False})

        self._prepare_carrier(
            self._prepare_carrier_product(list_price=7.5),
            name="Local Shipping",
            country_ids=[Command.set(self.country_us.ids)],
            state_ids=[Command.set(self.env.ref('base.state_us_5').ids)],
            website_published=True,
            fixed_price=50.0,
        )
        self.update_items()
        self.assertEqual(
            [{'country': 'US', 'region': 'CA', 'service': 'Local Shipping', 'price': '50.0 USD'}],
            self.red_sofa_item['shipping'],
        )

    def test_02_meta_shipping_rate_without_region(self):
        self.env['delivery.carrier'].search([]).write({'website_published': False})

        # Prepare a carrier for both US and Belgium
        self._prepare_carrier(
            self._prepare_carrier_product(list_price=15.0),
            name="World Carrier",
            country_ids=[Command.set((self.country_us + self.country_be).ids)],
            website_published=True,
            fixed_price=100.0,
        )

        self.update_items()

        expected_shipping = [
            {'country': 'US', 'region': '', 'service': 'World Carrier', 'price': '100.0 USD'},
            {'country': 'BE', 'region': '', 'service': 'World Carrier', 'price': '100.0 USD'},
        ]

        actual_shipping = sorted(self.red_sofa_item['shipping'], key=lambda s: s['country'])
        expected_shipping = sorted(expected_shipping, key=lambda s: s['country'])

        self.assertEqual(expected_shipping, actual_shipping)

    def test_03_meta_shipping_multiple_states(self):
        self.env['delivery.carrier'].search([]).write({'website_published': False})

        self._prepare_carrier(
            self._prepare_carrier_product(list_price=6.0),
            name="State-based Carrier",
            country_ids=[Command.set((self.country_us + self.country_be).ids)],
            state_ids=[
                Command.set([
                    self.env.ref('base.state_us_5').id,   # CA
                    self.env.ref('base.state_us_27').id,  # NY
                    self.env.ref('base.state_be_1').id,   # VAN
                ]),
            ],
            website_published=True,
            fixed_price=60.0,
        )

        # Force update using all countries — no filters
        self.update_items()

        actual_shipping = sorted(
            self.red_sofa_item['shipping'], key=lambda x: (x['country'], x['region']),
        )
        expected_shipping = sorted([
            {
                'country': 'US',
                'region': 'CA',
                'service': 'State-based Carrier',
                'price': '60.0 USD',
            },
            {
                'country': 'US',
                'region': 'NY',
                'service': 'State-based Carrier',
                'price': '60.0 USD',
            },
            {
                'country': 'BE',
                'region': 'VAN',
                'service': 'State-based Carrier',
                'price': '60.0 USD',
            },
        ], key=lambda x: (x['country'], x['region']))

        self.assertEqual(expected_shipping, actual_shipping)
