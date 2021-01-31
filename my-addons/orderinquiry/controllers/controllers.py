# -*- coding: utf-8 -*-
# from odoo import http


# class Orderinquiry(http.Controller):
#     @http.route('/orderinquiry/orderinquiry/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/orderinquiry/orderinquiry/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('orderinquiry.listing', {
#             'root': '/orderinquiry/orderinquiry',
#             'objects': http.request.env['orderinquiry.orderinquiry'].search([]),
#         })

#     @http.route('/orderinquiry/orderinquiry/objects/<model("orderinquiry.orderinquiry"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('orderinquiry.object', {
#             'object': obj
#         })
