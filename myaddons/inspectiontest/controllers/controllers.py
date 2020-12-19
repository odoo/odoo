# -*- coding: utf-8 -*-
# from odoo import http


# class Pltest(http.Controller):
#     @http.route('/pltest/pltest/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/pltest/pltest/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('pltest.listing', {
#             'root': '/pltest/pltest',
#             'objects': http.request.env['pltest.pltest'].search([]),
#         })

#     @http.route('/pltest/pltest/objects/<model("pltest.pltest"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('pltest.object', {
#             'object': obj
#         })
