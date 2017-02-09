# -*- coding: utf-8 -*-
from odoo import http

# class WebsiteSaleWishlist(http.Controller):
#     @http.route('/website_sale_wishlist/website_sale_wishlist/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/website_sale_wishlist/website_sale_wishlist/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('website_sale_wishlist.listing', {
#             'root': '/website_sale_wishlist/website_sale_wishlist',
#             'objects': http.request.env['website_sale_wishlist.website_sale_wishlist'].search([]),
#         })

#     @http.route('/website_sale_wishlist/website_sale_wishlist/objects/<model("website_sale_wishlist.website_sale_wishlist"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('website_sale_wishlist.object', {
#             'object': obj
#         })