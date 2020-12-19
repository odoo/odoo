# -*- coding: utf-8 -*-
# from odoo import http


# class IntegratedInheritance(http.Controller):
#     @http.route('/integrated_inheritance/integrated_inheritance/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/integrated_inheritance/integrated_inheritance/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('integrated_inheritance.listing', {
#             'root': '/integrated_inheritance/integrated_inheritance',
#             'objects': http.request.env['integrated_inheritance.integrated_inheritance'].search([]),
#         })

#     @http.route('/integrated_inheritance/integrated_inheritance/objects/<model("integrated_inheritance.integrated_inheritance"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('integrated_inheritance.object', {
#             'object': obj
#         })
