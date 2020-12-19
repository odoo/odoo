# -*- coding: utf-8 -*-
# from odoo import http


# class OrderInheritance(http.Controller):
#     @http.route('/order_inheritance/order_inheritance/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/order_inheritance/order_inheritance/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('order_inheritance.listing', {
#             'root': '/order_inheritance/order_inheritance',
#             'objects': http.request.env['order_inheritance.order_inheritance'].search([]),
#         })

#     @http.route('/order_inheritance/order_inheritance/objects/<model("order_inheritance.order_inheritance"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('order_inheritance.object', {
#             'object': obj
#         })
