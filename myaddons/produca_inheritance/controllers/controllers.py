# -*- coding: utf-8 -*-
# from odoo import http


# class Produca(http.Controller):
#     @http.route('/produca/produca/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/produca/produca/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('produca.listing', {
#             'root': '/produca/produca',
#             'objects': http.request.env['produca.produca'].search([]),
#         })

#     @http.route('/produca/produca/objects/<model("produca.produca"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('produca.object', {
#             'object': obj
#         })
