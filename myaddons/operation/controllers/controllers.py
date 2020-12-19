# -*- coding: utf-8 -*-
# from odoo import http


# class Operation(http.Controller):
#     @http.route('/operation/operation/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/operation/operation/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('operation.listing', {
#             'root': '/operation/operation',
#             'objects': http.request.env['operation.operation'].search([]),
#         })

#     @http.route('/operation/operation/objects/<model("operation.operation"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('operation.object', {
#             'object': obj
#         })
