# -*- coding: utf-8 -*-
# from odoo import http


# class Openshoes(http.Controller):
#     @http.route('/openshoes/openshoes/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/openshoes/openshoes/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('openshoes.listing', {
#             'root': '/openshoes/openshoes',
#             'objects': http.request.env['openshoes.openshoes'].search([]),
#         })

#     @http.route('/openshoes/openshoes/objects/<model("openshoes.openshoes"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('openshoes.object', {
#             'object': obj
#         })
