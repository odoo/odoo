# coding: utf-8
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website.tools import MockRequest
from odoo.tests import TransactionCase, tagged

@tagged('post_install', '-at_install')
class WebsiteSaleVisitorTests(TransactionCase):

    def setUp(self):
        super().setUp()
        self.website = self.env.ref('website.default_website')
        self.WebsiteSaleController = WebsiteSale()
        self.cookies = {}

    def test_create_visitor_on_tracked_product(self):
        self.WebsiteSaleController = WebsiteSale()
        existing_visitors = self.env['website.visitor'].search([])
        existing_tracks = self.env['website.track'].search([])

        product = self.env['product.product'].create({
            'name': 'Storage Box',
            'website_published': True,
        })

        with MockRequest(self.env, website=self.website):
            self.cookies = self.WebsiteSaleController.products_recently_viewed_update(product.id)

        new_visitors = self.env['website.visitor'].search([('id', 'not in', existing_visitors.ids)])
        new_tracks = self.env['website.track'].search([('id', 'not in', existing_tracks.ids)])
        self.assertEqual(len(new_visitors), 1, "A visitor should be created after visiting a tracked product")
        self.assertEqual(len(new_tracks), 1, "A track should be created after visiting a tracked product")

        with MockRequest(self.env, website=self.website, cookies=self.cookies):
            self.WebsiteSaleController.products_recently_viewed_update(product.id)

        new_visitors = self.env['website.visitor'].search([('id', 'not in', existing_visitors.ids)])
        new_tracks = self.env['website.track'].search([('id', 'not in', existing_tracks.ids)])
        self.assertEqual(len(new_visitors), 1, "No visitor should be created after visiting another tracked product")
        self.assertEqual(len(new_tracks), 1, "No track should be created after visiting the same tracked product before 30 min")

        product = self.env['product.product'].create({
            'name': 'Large Cabinet',
            'website_published': True,
            'list_price': 320.0,
        })

        with MockRequest(self.env, website=self.website, cookies=self.cookies):
            self.WebsiteSaleController.products_recently_viewed_update(product.id)

        new_visitors = self.env['website.visitor'].search([('id', 'not in', existing_visitors.ids)])
        new_tracks = self.env['website.track'].search([('id', 'not in', existing_tracks.ids)])
        self.assertEqual(len(new_visitors), 1, "No visitor should be created after visiting another tracked product")
        self.assertEqual(len(new_tracks), 2, "A track should be created after visiting another tracked product")

    def test_dynamic_filter_newest_products(self):
        """Test that a product is not displayed anymore after
        changing it company."""
        new_company = self.env['res.company'].create({
            'name': 'Test Company',
        })
        public_user = self.env.ref('base.public_user')

        product = self.env['product.product'].create({
            'name': 'Test Product',
            'website_published': True,
            'sale_ok': True,
        })

        self.website = self.website.with_user(public_user).with_context(website_id=self.website.id)
        snippet_filter = self.env.ref('website_sale.dynamic_filter_newest_products')

        res = snippet_filter._prepare_values(16, [])
        res_products = [res_product['_record'] for res_product in res]
        self.assertIn(product, res_products)

        product.product_tmpl_id.company_id = new_company
        product.product_tmpl_id.flush(['company_id'], product.product_tmpl_id)

        res = snippet_filter._prepare_values(16, [])
        res_products = [res_product['_record'] for res_product in res]
        self.assertNotIn(product, res_products)

    def test_recently_viewed_company_changed(self):
        """Test that a product is :
        - displayed after visiting it
        - not displayed after changing it company."""
        new_company = self.env['res.company'].create({
            'name': 'Test Company',
        })
        public_user = self.env.ref('base.public_user')

        product = self.env['product.product'].create({
            'name': 'Test Product',
            'website_published': True,
            'sale_ok': True,
        })

        self.website = self.website.with_user(public_user).with_context(website_id=self.website.id)

        snippet_filter = self.env.ref('website_sale.dynamic_filter_latest_viewed_products')

        # BEFORE VISITING THE PRODUCT
        res = snippet_filter._prepare_values(16, [])
        self.assertFalse(res)

        # AFTER VISITING THE PRODUCT
        with MockRequest(self.website.env, website=self.website):
            self.cookies = self.WebsiteSaleController.products_recently_viewed_update(product.id)
        with MockRequest(self.website.env, website=self.website, cookies=self.cookies):
            res = snippet_filter._prepare_values(16, [])
        res_products = [res_product['_record'] for res_product in res]
        self.assertIn(product, res_products)

        # AFTER CHANGING PRODUCT COMPANY
        product.product_tmpl_id.company_id = new_company
        product.product_tmpl_id.flush(['company_id'], product.product_tmpl_id)
        with MockRequest(self.website.env, website=self.website, cookies=self.cookies):
            res = snippet_filter._prepare_values(16, [])
        self.assertFalse(res)
