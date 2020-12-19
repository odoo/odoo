# -*- coding: utf-8 -*-
# from odoo import http


# class SaleInheritance(http.Controller):
#     @http.route('/sale_inheritance/sale_inheritance/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_inheritance/sale_inheritance/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_inheritance.listing', {
#             'root': '/sale_inheritance/sale_inheritance',
#             'objects': http.request.env['sale_inheritance.sale_inheritance'].search([]),
#         })

#     @http.route('/sale_inheritance/sale_inheritance/objects/<model("sale_inheritance.sale_inheritance"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_inheritance.object', {
#             'object': obj
#         })
