# -*- coding: utf-8 -*-
from openerp import http

# class OptimaCustomInvoice(http.Controller):
#     @http.route('/optima_custom_invoice/optima_custom_invoice/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/optima_custom_invoice/optima_custom_invoice/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('optima_custom_invoice.listing', {
#             'root': '/optima_custom_invoice/optima_custom_invoice',
#             'objects': http.request.env['optima_custom_invoice.optima_custom_invoice'].search([]),
#         })

#     @http.route('/optima_custom_invoice/optima_custom_invoice/objects/<model("optima_custom_invoice.optima_custom_invoice"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('optima_custom_invoice.object', {
#             'object': obj
#         })