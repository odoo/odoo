# -*- coding: utf-8 -*-
from openerp import http

# class Sociolla(http.Controller):
#     @http.route('/sociolla/sociolla/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sociolla/sociolla/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('sociolla.listing', {
#             'root': '/sociolla/sociolla',
#             'objects': http.request.env['sociolla.sociolla'].search([]),
#         })

#     @http.route('/sociolla/sociolla/objects/<model("sociolla.sociolla"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sociolla.object', {
#             'object': obj
#         })