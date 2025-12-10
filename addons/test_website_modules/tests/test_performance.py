# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import re
from PIL import Image
from unittest.mock import patch
import odoo
from odoo.fields import Command
from odoo.tests import tagged
from odoo.addons.website.tests.test_performance import TestWebsitePerformanceCommon
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon
from odoo.addons.website_sale.tests.test_website_sale_pricelist import TestWebsitePriceList


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

        cats = cls.env['product.public.category'].create([{
            'name': 'Level 0',
        }, {
            'name': 'Level 1',
        }, {
            'name': 'Level 2',
        }])
        cats[2].parent_id = cats[1].id
        cats[1].parent_id = cats[0].id

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
            'public_categ_ids': [Command.link(cats[2].id)],
        })

        cls.productB = cls.env['product.product'].create({
            'name': 'Product B',
            'list_price': 100,
            'sale_ok': True,
            'website_published': True,
            'image_1920': red_image,
            'website_sequence': -10,
        })

        cls.templateC = cls.env['product.template'].create({
            'name': 'Test Remove Image',
            'image_1920': blue_image,
            'website_sequence': -10,
            'public_categ_ids': [Command.link(cats[1].id)],
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
                'image_1920': red_image,
                'website_sequence': -9,
                'attribute_line_ids': [
                    Command.create({
                        'attribute_id': cls.product_attribute.id,
                        'value_ids': [Command.set(cls.product_attribute.value_ids.ids)],
                    }),
                ],
            })
            variant = template.product_variant_ids[0]
            if i % 5:
                variant.website_published = True
            if i % 4:
                variant.website_sequence = -7

            images = [{
                'name': 'Template image',
                'image_1920': blue_image,
            }]
            if i % 2:
                images.append({
                    'name': 'Variant image',
                    'image_1920': red_image,
                    'product_variant_id': variant.id,
                })
            cls.env['product.image'].create(images)

        fpos = cls.env["account.fiscal.position"].create({
            'name': 'Fiscal Position BE',
            'country_id': cls.env.ref('base.be').id,
            'auto_apply': True,
            'sequence': -1,
        })
        usd = cls.env.ref('base.USD')
        cls.env['product.pricelist'].create({
            'name': 'Custom pricelist (TEST)',
            'currency_id': usd.id,
            'sequence': -1,
            'item_ids': [(0, 0, {
                'base': 'list_price',
                'applied_on': '1_product',
                'product_tmpl_id': cls.templateC.id,
                'price_discount': 20,
                'min_quantity': 2,
                'compute_price': 'formula',
            })],
        })
        tax_group = cls.env['account.tax.group'].create({'name': 'Test 6%'})
        cls.env['account.tax'].create({
                'name': "Test 6%",
                'fiscal_position_ids': fpos,
                'amount': 6,
                'price_include_override': 'tax_included',
                'type_tax_use': 'sale',
                'amount_type': 'percent',
                'country_id': cls.env.ref('base.us').id,
                'tax_group_id': tax_group.id,
        })

    def setUp(self):
        super().setUp()
        self.session = None
        self.env['website'].search([]).channel_id = False

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

    def _get_queries_shop(self):
        html = self.url_open('/shop').text
        self.assertIn(f'<img src="/web/image/product.product/{self.productC.id}/', html)
        self.assertIn(f'<img src="/web/image/product.template/{self.productA.product_tmpl_id.id}/', html)
        self.assertIn(f'<img src="/web/image/product.image/{self.product_images.ids[1]}/', html)

        query_count = 51  # To increase this number you must ask the permission to al
        queries = {
            'orm_signaling_registry': 1,
            'website': 2,
            'res_company': 2,
            'product_pricelist': 4,
            'product_template': 5,
            'product_tag': 1,
            'product_public_category': 6,
            'product_product': 1,
            'product_template_attribute_line': 3,
            'res_users': 1,
            'res_partner': 2,
            'product_category': 1,
            'product_pricelist_item': 2,
            'account_tax': 1,
            'res_currency': 1,
            'account_account_tag': 1,
            'product_ribbon': 1,
            'product_attribute_value': 3,
            'product_attribute': 1,
            'ir_attachment': 4,
            'product_image': 3,
            'product_template_attribute_value': 1,
            'ir_ui_view': 2,
            'website_menu': 1,
            'website_page': 1,
        }

        addons = tuple(self.env.registry._init_modules) + (self.env.context.get('install_module'),)
        if 'website_helpdesk' in addons:
            query_count += 1
            queries['helpdesk_team'] = 1
        if 'website_sale_subscription' in addons:
            query_count += 1
            queries['product_product'] += 1

        tax = self.env.ref('account.1_sale_tax_template', raise_if_not_found=False)
        if tax and tax.name == '15%':
            query_count += 2
            queries['account_tax_repartition_line'] = 2

        if self._has_demo_data():
            query_count += 5
            queries['product_template'] += 1
            queries['product_product'] += 2
            queries['ir_attachment'] += 1
            queries['product_ribbon'] += 1
        else:
            query_count += 3
            queries['product_template_attribute_value'] += 3

        # To increase the query count you must ask the permission to al
        return query_count, queries

    def _has_demo_data(self):
        return bool(self.env['ir.module.module'].search_count([('demo', '=', True)]))

    def test_perf_sql_queries_shop(self):
        # To increase the query count you must ask the permission to al
        query_count, queries = self._get_queries_shop()

        if self._has_demo_data():
            query_count += 5
            queries['account_tax'] += 1
            queries['account_account_tag'] += 2
            queries['product_template_attribute_value'] += 2

        self.assertEqual(sum(queries.values()), query_count, 'Please learn to count.')
        self._check_url_hot_query('/shop', query_count, queries)


@tagged('post_install', '-at_install')
class TestWebsiteAllPerformanceShop(TestWebsiteAllPerformance):

    def test_perf_sql_queries_shop(self):
        # To increase the query count you must ask the permission to al
        query_count, queries = self._get_queries_shop()

        query_count += 3
        queries['account_tax'] += 1
        queries['account_account_tag'] += 2

        if self._has_demo_data():
            query_count += 2
            queries['product_template_attribute_value'] += 2

        self.assertEqual(sum(queries.values()), query_count, 'Please learn to count.')
        self._check_url_hot_query('/shop', query_count, queries)
