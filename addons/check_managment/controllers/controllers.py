# -*- coding: utf-8 -*-
from openerp import http

# class Utravel1(http.Controller):
#     @http.route('/utravel_1/utravel_1/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/utravel_1/utravel_1/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('utravel_1.listing', {
#             'root': '/utravel_1/utravel_1',
#             'objects': http.request.env['utravel_1.utravel_1'].search([]),
#         })

#     @http.route('/utravel_1/utravel_1/objects/<model("utravel_1.utravel_1"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('utravel_1.object', {
#             'object': obj
#         })