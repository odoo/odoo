# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah

from odoo import http

# class Default(http.Controller):
#     @http.route('/default/default/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/default/default/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('default.listing', {
#             'root': '/default/default',
#             'objects': http.request.env['default.default'].search([]),
#         })

#     @http.route('/default/default/objects/<model("default.default"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('default.object', {
#             'object': obj
#         })
