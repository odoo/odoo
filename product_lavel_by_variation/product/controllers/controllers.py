# -*- coding: utf-8 -*-
# from odoo import http


# class Product(http.Controller):
#     @http.route('/product/product', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/product/product/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('product.listing', {
#             'root': '/product/product',
#             'objects': http.request.env['product.product'].search([]),
#         })

#     @http.route('/product/product/objects/<model("product.product"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('product.object', {
#             'object': obj
#         })
