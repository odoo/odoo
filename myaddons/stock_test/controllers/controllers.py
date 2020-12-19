# -*- coding: utf-8 -*-
# from odoo import http


# class StockTest(http.Controller):
#     @http.route('/stock_test/stock_test/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/stock_test/stock_test/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('stock_test.listing', {
#             'root': '/stock_test/stock_test',
#             'objects': http.request.env['stock_test.stock_test'].search([]),
#         })

#     @http.route('/stock_test/stock_test/objects/<model("stock_test.stock_test"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('stock_test.object', {
#             'object': obj
#         })
