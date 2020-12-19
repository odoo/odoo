# -*- coding: utf-8 -*-
# from odoo import http


# class Mode(http.Controller):
#     @http.route('/mode/mode/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mode/mode/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('mode.listing', {
#             'root': '/mode/mode',
#             'objects': http.request.env['mode.mode'].search([]),
#         })

#     @http.route('/mode/mode/objects/<model("mode.mode"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mode.object', {
#             'object': obj
#         })
