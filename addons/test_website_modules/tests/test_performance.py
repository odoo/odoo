# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import re
from unittest.mock import patch

from PIL import Image

import odoo
from odoo.tests import tagged

from odoo.addons.website.tests.test_performance import TestWebsitePerformanceCommon
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon
from odoo.addons.website_sale.tests.test_pricelist import TestWebsitePriceList


class TestWebsiteAllPerformance(TestWebsitePerformanceCommon, TestWebsitePriceList, WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Attachment needed for the replacement of images
        cls.env['ir.attachment'].create({
            'public': True,
            'name': 's_default_image.jpg',
            'type': 'url',
            'url': f'{cls.base_url()}/web/image/website.s_banner_default_image.jpg',
        })

        # First image (blue) for the template.
        color_blue = '#4169E1'
        name_blue = 'Royal Blue'
        # Red for the variant.
        color_red = '#CD5C5C'
        name_red = 'Indian Red'

        # Create the color attribute.
        cls.product_attribute = cls.env['product.attribute'].create({
            'name': 'Beautiful Color',
            'display_type': 'color',
        })

        # create the color attribute values
        cls.attr_values = cls.env['product.attribute.value'].create([{
            'name': name_blue,
            'attribute_id': cls.product_attribute.id,
            'html_color': color_blue,
            'sequence': 1,
        }, {
            'name': name_red,
            'attribute_id': cls.product_attribute.id,
            'html_color': color_red,
            'sequence': 2,
        },
        ])

        # first image (blue) for the template
        f = io.BytesIO()
        Image.new('RGB', (1920, 1080), '#4169E1').save(f, 'JPEG')
        f.seek(0)
        blue_image = base64.b64encode(f.read())

        # second image (red) for the variant 1
        f = io.BytesIO()
        Image.new('RGB', (800, 500), '#FF69E1').save(f, 'JPEG')
        f.seek(0)
        red_image = base64.b64encode(f.read())

        cls.productA = cls.env['product.product'].create({
            'name': 'Product A',
            'list_price': 100,
            'sale_ok': True,
            'website_published': True,
            'website_sequence': 1,
        })

        cls.productB = cls.env['product.product'].create({
            'name': 'Product B',
            'list_price': 100,
            'sale_ok': True,
            'website_published': True,
            'image_1920': red_image,
        })

        cls.templateC = cls.env['product.template'].create({
            'name': 'Test Remove Image',
            'image_1920': blue_image,
            'website_sequence': 1,
        })
        cls.productC = cls.templateC.product_variant_ids[0]
        cls.productC.write({
            'name': 'Product C',
            'list_price': 100,
            'sale_ok': True,
            'website_published': True,
        })
        cls.product_images = cls.env['product.image'].with_context(default_product_tmpl_id=cls.productC.product_tmpl_id.id).create([{
            'name': 'Template image',
            'image_1920': blue_image,
        }, {
            'name': 'Variant image',
            'image_1920': red_image,
            'product_variant_id': cls.productC.id,
        }])

        for i in range(20):
            template = cls.env['product.template'].create({
                'name': f'Product test {i}',
                'list_price': 100,
                'sale_ok': True,
                'website_published': True,
                'image_1920': red_image,
            })
            images = [{
                'name': 'Template image',
                'image_1920': blue_image,
            }]
            if i % 2:
                images.append({
                    'name': 'Variant image',
                    'image_1920': red_image,
                    'product_variant_id': template.product_variant_ids[0].id,
                })

    def setUp(self):
        super().setUp()
        self.session = None
        self.env['website'].search([]).channel_id = False

    def test_perf_sql_queries_shop(self):
        html = self.url_open('/shop').text
        self.assertIn(f'<img src="/web/image/product.product/{self.productC.id}/', html)
        self.assertIn(f'<img src="/web/image/product.template/{self.productA.product_tmpl_id.id}/', html)
        self.assertIn(f'<img src="/web/image/product.image/{self.product_images.ids[1]}/', html)

        # Test in community: 36
        self.assertLessEqual(self._get_url_hot_query('/shop'), 37)  # To increase this number you must ask the permission to al

    def _get_cart_quantity(self):
        return int(re.search(
            r'my_cart_quantity.*?>([0-9.]+)</sup>',
            self.url_open(self.page.url).text
        ).group(1))

    def test_website_user_id_public_user(self):
        origin_serve_page = odoo.addons.website.models.ir_http.IrHttp._serve_page

        def _serve_page():
            request = odoo.http.request
            self.assertTrue(request.env['website'].search([]).user_id._is_public(), 'The public user of the website is not public!')
            self.assertTrue(request.env.user._is_public(), 'The visitor should not be logged')
            return origin_serve_page()

        with patch('odoo.addons.website.models.ir_http.IrHttp._serve_page', wraps=_serve_page) as mocked:
            self.url_open(self.page.url)
            mocked.assert_called_once()

    def test_perf_sql_queries_page(self):
        self.set_registry_readonly_mode(True)
        self.page.track = False

        # self.url_open('/web/set_profiling?profile=1&execution_context_qweb=1')

        self.assertEqual(self._get_cart_quantity(), 0)

        origin_allow_to_use_cache = odoo.addons.website.models.website_page.WebsitePage._allow_to_use_cache

        def _allow_to_use_cache(request):
            can_use = origin_allow_to_use_cache(request.env['website.page'], request)
            self.assertTrue(can_use, 'The homepage should be cached for the public user')

        with patch('odoo.addons.website.models.website_page.WebsitePage._allow_to_use_cache', wraps=_allow_to_use_cache) as mocked:
            self.url_open(self.page.url)
            mocked.assert_called_once()

        select_tables_perf = {
            # website queries
            'orm_signaling_registry': 1,
            'ir_attachment': 1,
            # website_livechat _post_process_response_from_cache queries
            'website': 1,
            # website_crm_iap_reveal _serve_page queries
            'website_visitor': 1,
        }
        expected_query_count = sum(select_tables_perf.values())
        self._check_url_hot_query(self.page.url, expected_query_count, select_tables_perf, {})

        self.url_open('/shop/cart/add', json={
            "id": 0,
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "product_template_id": self.productC.product_tmpl_id.id,
                "product_id": self.productC.id,
                "quantity": 1,
                "uom_id": 1,
                "product_custom_attribute_values": [],
                "no_variant_attribute_value_ids": [],
                "linked_products": []
            }
        })
        self.assertEqual(self._get_cart_quantity(), 1)
        select_tables_perf = {
            # website queries
            'orm_signaling_registry': 1,
            'ir_attachment': 1,
            # website_livechat _post_process_response_from_cache queries
            'website': 1,
            # website_crm_iap_reveal _serve_page queries
            'website_visitor': 1,
        }
        expected_query_count = sum(select_tables_perf.values())
        self._check_url_hot_query(self.page.url, expected_query_count, select_tables_perf, {})

        self.url_open('/shop/cart/update', json={
            "id": 0,
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "line_id": self.env['sale.order'].search([], limit=1).order_line.id,
                "product_id": self.productC.id,
                "quantity": 0
            }
        })

        self.assertEqual(self._get_cart_quantity(), 0)
        select_tables_perf = {
            # website queries
            'orm_signaling_registry': 1,
            'ir_attachment': 1,
            # website_livechat _post_process_response_from_cache queries
            'website': 1,
            # website_crm_iap_reveal _serve_page queries
            'website_visitor': 1,
        }
        expected_query_count = sum(select_tables_perf.values())
        self._check_url_hot_query(self.page.url, expected_query_count, select_tables_perf, {})


@tagged('post_install', '-at_install')
class TestWebsiteAllPerformancePostInstall(TestWebsiteAllPerformance):

    def test_perf_sql_queries_shop(self):
        tax_group = self.env['account.tax.group'].create({'name': 'Tax 15%'})
        tax = self.env['account.tax'].create({
            'name': 'Tax 15%',
            'amount': 15,
            'type_tax_use': 'sale',
            'tax_group_id': tax_group.id,
            'country_id': self.env.company.country_id.id,
        })
        self.productB.taxes_id = tax

        html = self.url_open('/shop').text
        self.assertIn(f'<img src="/web/image/product.product/{self.productC.id}/', html)
        self.assertIn(f'<img src="/web/image/product.template/{self.productA.product_tmpl_id.id}/', html)
        self.assertIn(f'<img src="/web/image/product.image/{self.product_images.ids[1]}/', html)

        # Test in community: 45
        self.assertLessEqual(self._get_url_hot_query('/shop'), 47)  # To increase this number you must ask the permission to al
