# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests import HttpCase, tagged
from odoo.addons.website.tools import MockRequest

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install', 'website_snippets')
class TestSnippets(HttpCase):

    def test_01_snippet_products_edition(self):
        self.env['product.product'].create({
            'name': 'Test Product',
            'website_published': True,
            'sale_ok': True,
            'list_price': 500,
        })
        self.env['product.product'].create({
            'name': 'Test Product 2',
            'website_published': True,
            'sale_ok': True,
            'list_price': 500,
        })
        self.env['product.product'].create({
            'name': 'Test Product 3',
            'website_published': True,
            'sale_ok': True,
            'list_price': 500,
        })
        self.env['product.product'].create({
            'name': 'Test Product 4',
            'website_published': True,
            'sale_ok': True,
            'list_price': 500,
        })
        self.start_tour('/', 'website_sale.snippet_products', login='admin')

    def test_02_snippet_products_remove(self):
        self.user = self.env['res.users'].search([('login', '=', 'admin')])
        self.website_visitor = self.env['website.visitor'].search([('partner_id', '=', self.user.partner_id.id)])
        before_tour_product_ids = self.website_visitor.product_ids.ids
        with MockRequest(self.env, website=self.env['website'].get_current_website()):
            if not self.website_visitor:
                self.website_visitor = self.env['website.visitor'].create({'partner_id': self.user.partner_id.id})
            self.product = self.env['product.product'].create({
                'name': 'Storage Box',
                'website_published': True,
                'image_512': b'/product/static/img/product_product_9-image.jpg',
                'display_name': 'Bin',
                'description_sale': 'Pedal-based opening system',
            })
            self.website_visitor._add_viewed_product(self.product.id)
            self.start_tour('/', 'website_sale.products_snippet_recently_viewed', login='admin')
            after_tour_product_ids = self.website_visitor.product_ids.ids
            self.assertEqual(before_tour_product_ids, after_tour_product_ids, "There shouldn't be any new product in recently viewed after this tour")
