# -*- coding: utf-8 -*-
# from odoo import http


# class Maria(http.Controller):
#     @http.route('/maria/maria', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/maria/maria/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('maria.listing', {
#             'root': '/maria/maria',
#             'objects': http.request.env['maria.maria'].search([]),
#         })

#     @http.route('/maria/maria/objects/<model("maria.maria"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('maria.object', {
#             'object': obj
#         })

