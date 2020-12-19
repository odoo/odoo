# -*- coding: utf-8 -*-
from odoo import http

# class ReceiptMan(http.Controller):
#     @http.route('/receipt_man/receipt_man/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/receipt_man/receipt_man/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('receipt_man.listing', {
#             'root': '/receipt_man/receipt_man',
#             'objects': http.request.env['receipt_man.receipt_man'].search([]),
#         })

#     @http.route('/receipt_man/receipt_man/objects/<model("receipt_man.receipt_man"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('receipt_man.object', {
#             'object': obj
#         })