# -*- coding: utf-8 -*-
from odoo import http

# class SaleQuotePay(http.Controller):
#     @http.route('/sale_quote_pay/sale_quote_pay/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_quote_pay/sale_quote_pay/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_quote_pay.listing', {
#             'root': '/sale_quote_pay/sale_quote_pay',
#             'objects': http.request.env['sale_quote_pay.sale_quote_pay'].search([]),
#         })

#     @http.route('/sale_quote_pay/sale_quote_pay/objects/<model("sale_quote_pay.sale_quote_pay"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_quote_pay.object', {
#             'object': obj
#         })