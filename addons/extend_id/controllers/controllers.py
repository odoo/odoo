# -*- coding: utf-8 -*-
# from odoo import http


# class ExtendId(http.Controller):
#     @http.route('/extend_id/extend_id/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/extend_id/extend_id/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('extend_id.listing', {
#             'root': '/extend_id/extend_id',
#             'objects': http.request.env['extend_id.extend_id'].search([]),
#         })

#     @http.route('/extend_id/extend_id/objects/<model("extend_id.extend_id"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('extend_id.object', {
#             'object': obj
#         })
