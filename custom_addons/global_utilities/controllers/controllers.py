# -*- coding: utf-8 -*-
# from odoo import http


# class GlobalUtilities(http.Controller):
#     @http.route('/global_utilities/global_utilities', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/global_utilities/global_utilities/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('global_utilities.listing', {
#             'root': '/global_utilities/global_utilities',
#             'objects': http.request.env['global_utilities.global_utilities'].search([]),
#         })

#     @http.route('/global_utilities/global_utilities/objects/<model("global_utilities.global_utilities"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('global_utilities.object', {
#             'object': obj
#         })

