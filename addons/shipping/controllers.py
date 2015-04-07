# -*- coding: utf-8 -*-
from openerp import http

# class Shipping(http.Controller):
#     @http.route('/shipping/shipping/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/shipping/shipping/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('shipping.listing', {
#             'root': '/shipping/shipping',
#             'objects': http.request.env['shipping.shipping'].search([]),
#         })

#     @http.route('/shipping/shipping/objects/<model("shipping.shipping"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('shipping.object', {
#             'object': obj
#         })