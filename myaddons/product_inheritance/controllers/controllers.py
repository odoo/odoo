# -*- coding: utf-8 -*-
# from odoo import http


# class ProductInheritance(http.Controller):
#     @http.route('/product_inheritance/product_inheritance/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/product_inheritance/product_inheritance/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('product_inheritance.listing', {
#             'root': '/product_inheritance/product_inheritance',
#             'objects': http.request.env['product_inheritance.product_inheritance'].search([]),
#         })

#     @http.route('/product_inheritance/product_inheritance/objects/<model("product_inheritance.product_inheritance"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('product_inheritance.object', {
#             'object': obj
#         })
