# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

import string
from collections import defaultdict
from odoo import http
from odoo.http import request
from odoo.addons.website.controllers.main import Website
from odoo.addons.website_sale.controllers.main import WebsiteSale


class ProductBrnadKnkWebsiteSale(WebsiteSale):
    def _get_search_options(
        self, category=None, attrib_values=None, pricelist=None, min_price=0.0, max_price=0.0, conversion_rate=1, **post
    ):
        res = super(ProductBrnadKnkWebsiteSale, self)._get_search_options(category, attrib_values, pricelist, min_price, max_price, conversion_rate, **post)
        if request.params.get('brand', False):
            request_args = request.httprequest.args
            selected_brands = [int(x) for x in request_args.getlist('brand')]
            res['brand'] = selected_brands
        return res

    @http.route()
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        response = super().shop(page=page, category=category, search=search, min_price=min_price, max_price=max_price, ppg=ppg, **post)
        request_args = request.httprequest.args
        selected_brands = [int(x) for x in request_args.getlist('brand')]
        response.qcontext.update(
            brands=request.env['product.brand'].search([]),
            selected_brands=selected_brands,
        )
        return response


class ProductBrnadKnkWebsite(http.Controller):

    @http.route('/shop/all_brands', type='http', auth='public', website=True)
    def all_brands(self, **args):
        brands = request.env['product.brand'].search([])
        brands = brands.filtered(lambda l: len(l.product_ids.filtered(lambda p: p.is_published)) > 0)
        brands_group_by_alphabet = {'All Brands': brands}
        is_disable_grouping = True

        if is_disable_grouping:
            brands_group_by_alphabet = {'All Brands': brands}
        else:
            alphabet_range = string.ascii_uppercase
            brands_group_by_alphabet = defaultdict(list)
            brands_group_by_alphabet.update((alphabet, []) for alphabet in alphabet_range)
            for brand in brands:
                first_char = str.upper(brand.name[:1])
                brands_group_by_alphabet[first_char].append(brand)
        return request.render('product_brand_knk.all_brands', {
            'is_disable_grouping': is_disable_grouping,
            'grouped_brands': brands_group_by_alphabet
        })
