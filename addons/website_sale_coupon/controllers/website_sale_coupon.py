# -*- coding: utf-8 -*-
from openerp import http

# class WebsiteSaleCoupon(http.Controller):
#     @http.route('/website_sale_coupon/website_sale_coupon/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/website_sale_coupon/website_sale_coupon/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('website_sale_coupon.listing', {
#             'root': '/website_sale_coupon/website_sale_coupon',
#             'objects': http.request.env['website_sale_coupon.website_sale_coupon'].search([]),
#         })

#     @http.route('/website_sale_coupon/website_sale_coupon/objects/<model("website_sale_coupon.website_sale_coupon"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('website_sale_coupon.object', {
#             'object': obj
#         })