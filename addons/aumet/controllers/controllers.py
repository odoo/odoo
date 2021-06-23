# -*- coding: utf-8 -*-
# from odoo import http


# class Aumet(http.Controller):
#     @http.route('/aumet/aumet/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/aumet/aumet/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('aumet.listing', {
#             'root': '/aumet/aumet',
#             'objects': http.request.env['aumet.aumet'].search([]),
#         })

#     @http.route('/aumet/aumet/objects/<model("aumet.aumet"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('aumet.object', {
#             'object': obj
#         })
