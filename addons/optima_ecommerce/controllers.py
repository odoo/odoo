# -*- coding: utf-8 -*-
from openerp import http

# class OptimaEcommerce(http.Controller):
#     @http.route('/optima_ecommerce/optima_ecommerce/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/optima_ecommerce/optima_ecommerce/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('optima_ecommerce.listing', {
#             'root': '/optima_ecommerce/optima_ecommerce',
#             'objects': http.request.env['optima_ecommerce.optima_ecommerce'].search([]),
#         })

#     @http.route('/optima_ecommerce/optima_ecommerce/objects/<model("optima_ecommerce.optima_ecommerce"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('optima_ecommerce.object', {
#             'object': obj
#         })