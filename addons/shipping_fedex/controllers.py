# -*- coding: utf-8 -*-
from openerp import http

# class ShippingFedex(http.Controller):
#     @http.route('/shipping_fedex/shipping_fedex/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/shipping_fedex/shipping_fedex/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('shipping_fedex.listing', {
#             'root': '/shipping_fedex/shipping_fedex',
#             'objects': http.request.env['shipping_fedex.shipping_fedex'].search([]),
#         })

#     @http.route('/shipping_fedex/shipping_fedex/objects/<model("shipping_fedex.shipping_fedex"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('shipping_fedex.object', {
#             'object': obj
#         })