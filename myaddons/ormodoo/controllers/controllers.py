# -*- coding: utf-8 -*-
# from odoo import http


# class Ormodoo(http.Controller):
#     @http.route('/ormodoo/ormodoo/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ormodoo/ormodoo/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('ormodoo.listing', {
#             'root': '/ormodoo/ormodoo',
#             'objects': http.request.env['ormodoo.ormodoo'].search([]),
#         })

#     @http.route('/ormodoo/ormodoo/objects/<model("ormodoo.ormodoo"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ormodoo.object', {
#             'object': obj
#         })
