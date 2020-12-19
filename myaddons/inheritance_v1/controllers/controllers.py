# -*- coding: utf-8 -*-
# from odoo import http


# class InheritanceV1(http.Controller):
#     @http.route('/inheritance_v1/inheritance_v1/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/inheritance_v1/inheritance_v1/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('inheritance_v1.listing', {
#             'root': '/inheritance_v1/inheritance_v1',
#             'objects': http.request.env['inheritance_v1.inheritance_v1'].search([]),
#         })

#     @http.route('/inheritance_v1/inheritance_v1/objects/<model("inheritance_v1.inheritance_v1"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('inheritance_v1.object', {
#             'object': obj
#         })
