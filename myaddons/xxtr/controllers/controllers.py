# -*- coding: utf-8 -*-
# from odoo import http


# class Xxtr(http.Controller):
#     @http.route('/xxtr/xxtr/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/xxtr/xxtr/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('xxtr.listing', {
#             'root': '/xxtr/xxtr',
#             'objects': http.request.env['xxtr.xxtr'].search([]),
#         })

#     @http.route('/xxtr/xxtr/objects/<model("xxtr.xxtr"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('xxtr.object', {
#             'object': obj
#         })
