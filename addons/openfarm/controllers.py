# -*- coding: utf-8 -*-
from openerp import http

# class Openfarm(http.Controller):
#     @http.route('/openfarm/openfarm/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/openfarm/openfarm/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('openfarm.listing', {
#             'root': '/openfarm/openfarm',
#             'objects': http.request.env['openfarm.openfarm'].search([]),
#         })

#     @http.route('/openfarm/openfarm/objects/<model("openfarm.openfarm"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('openfarm.object', {
#             'object': obj
#         })