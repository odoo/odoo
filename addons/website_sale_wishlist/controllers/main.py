# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
import json


class WebsiteSaleWishlist(WebsiteSale):

    @http.route(['/shop/wishlist/add'], type='json', auth="user", website=True)
    def add_to_wishlist(self, product_id, price=False, **kw):
        if not price:
            compute_currency, pricelist_context, pl = self._get_compute_currency_and_context()
            p = request.env['product.product'].with_context(pricelist_context, display_default_code=False).browse(product_id)
            price = p.website_price

        request.env['product.wishlist']._add_to_wishlist(
            request.env.user.partner_id.id,
            pl.id,
            pl.currency_id.id,
            request.website.id,
            price,
            product_id
        )
        return True

    @http.route(['/shop/wishlist'], type='http', auth="user", website=True)
    def get_wishlist(self, count=False, **kw):
        values = request.env['product.wishlist'].with_context(display_default_code=False).search([('partner_id', '=', request.env.user.partner_id.id)])
        if count:
            return request.make_response(json.dumps(values.mapped('product_id').ids))

        if not len(values):
            return request.redirect("/shop")

        return request.render("website_sale_wishlist.product_wishlist", dict(wishes=values))
