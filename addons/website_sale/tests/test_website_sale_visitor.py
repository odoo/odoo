# coding: utf-8
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website.tools import MockRequest
from odoo.tests import TransactionCase, tagged

@tagged('post_install', '-at_install')
class WebsiteSaleVisitorTests(TransactionCase):

    def setUp(self):
        super().setUp()
        self.website = self.env['website'].browse(1)
        self.WebsiteSaleController = WebsiteSale()
        self.cookies = {}

    def test_create_visitor_on_tracked_product(self):
        self.WebsiteSaleController = WebsiteSale()
        Visitor = self.env['website.visitor']
        Track = self.env['website.track']

        self.assertEqual(len(Visitor.search([])), 0, "No visitor at the moment")
        self.assertEqual(len(Track.search([])), 0, "No track at the moment")

        product = self.env.ref('product.product_product_7')

        with MockRequest(self.env, website=self.website):
            self.cookies = self.WebsiteSaleController.products_recently_viewed_update(product.id)

        self.assertEqual(len(Visitor.search([])), 1, "A visitor should be created after visiting a tracked product")
        self.assertEqual(len(Track.search([])), 1, "A track should be created after visiting a tracked product")

        with MockRequest(self.env, website=self.website, cookies=self.cookies):
            self.WebsiteSaleController.products_recently_viewed_update(product.id)

        self.assertEqual(len(Visitor.search([])), 1, "No visitor should be created after visiting another tracked product")
        self.assertEqual(len(Track.search([])), 1, "No track should be created after visiting the same tracked product before 30 min")

        product = self.env.ref('product.product_product_6')
        with MockRequest(self.env, website=self.website, cookies=self.cookies):
            self.WebsiteSaleController.products_recently_viewed_update(product.id)

        self.assertEqual(len(Visitor.search([])), 1, "No visitor should be created after visiting another tracked product")
        self.assertEqual(len(Track.search([])), 2, "A track should be created after visiting another tracked product")
