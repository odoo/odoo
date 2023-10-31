# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Vishnu P(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import time
from odoo import http
from odoo.http import request


class DynamicSnippets(http.Controller):
    """This class is for the getting values for dynamic product snippets
       """
    @http.route('/top_selling_products', type='json', auth='public')
    def top_selling(self):
        """Function for getting the current website,top sold products and
           its categories.
            Return
                  products-most sold products
                  unique_categories-categories of all products
                  current_website-the current website for checking products or
            """
        current_website = request.env['website'].sudo().get_current_website().id
        public_categ_id = request.env[
            'product.public.category'].sudo().search_read([], ['name',
                                                               'website_id'])
        products = []
        public_categories = []
        for category in public_categ_id:
            products_search_read = request.env['product.template'].with_user(
                1).search_read(
                [('is_published', '=', True),
                 ('public_categ_ids.id', '=', category['id'])],
                ['name', 'image_1920', 'public_categ_ids', 'website_id',
                 'sales_count', 'list_price'], order='sales_count')
            for product in products_search_read:
                if product['sales_count'] != 0:
                    products.append(product)
                    public_categories.append(category)
        unique_categories = [dict(categories) for categories in
                             {tuple(sorted(record.items())) for record in
                              public_categories}]
        products = sorted(products, key=lambda i: i['sales_count'],
                          reverse=True)
        unique_id = "pc-%d" % int(time.time() * 1000)
        return products, unique_categories, current_website, unique_id

    @http.route('/new_arrival_products', type='json', auth='public')
    def products_new_arrivals(self):
        """Function for getting the current website,new arrival products and
           its categories.
            Return
                  products-most sold products
                  unique_categories-categories of all products
                  current_website-the current website for checking products or
        """
        current_website = request.env[
            'website'].sudo().get_current_website().id
        public_categ_id = request.env[
            'product.public.category'].sudo().search_read([], ['name',
                                                               'website_id'])
        products = []
        public_categories = []
        for category in public_categ_id:
            products_search_read = request.env['product.template'].with_user(
                1).search_read(
                [('is_published', '=', True),
                 ('public_categ_ids.id', '=', category['id'])],
                ['name', 'public_categ_ids', 'website_id',
                 'sales_count', 'image_1920', 'list_price', 'create_date'],
                order='create_date desc')
            for product in products_search_read:
                products.append(product)
                public_categories.append(category)
        unique_id = "uc-%d" % int(time.time() * 1000)
        unique_categories = [dict(categories) for categories in
                             {tuple(sorted(record.items())) for record in
                              public_categories}]
        products = sorted(products, key=lambda i: i['create_date'],
                          reverse=True)
        return products, unique_categories, current_website, unique_id

    @http.route('/top_rated_products', type='json', auth='public')
    def top_rated_products(self):
        """Function for getting the current website,rated products and
           its categories.
            Return
                  products-most sold products
                  unique_categories-categories of all products
                  current_website-the current website for checking products or
        """
        current_website = request.env[
            'website'].sudo().get_current_website().id
        public_categ_id = request.env[
            'product.public.category'].sudo().search_read([], ['name',
                                                               'website_id'])
        rated_products = request.env['rating.rating'].sudo().search_read(
            [('res_model', '=', 'product.template')],
            ['res_id', 'res_name', ], order='rating desc')
        products = []
        public_categories = []
        for category in rated_products:
            products_search_read = request.env['product.template'].with_user(
                1).search_read(
                [('is_published', '=', True),
                 ('id', '=', category['res_id'])],
                ['name', 'public_categ_ids', 'website_id',
                 'sales_count', 'image_1920', 'list_price', 'create_date'],)
            for product in products_search_read:
                if not product in products:
                    products.append(product)
                    public_categories.append(category)
        unique_categories = [dict(categories) for categories in
                             {tuple(sorted(record.items())) for record in
                              public_categories}]
        return products, unique_categories, current_website, public_categ_id
