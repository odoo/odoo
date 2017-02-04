# -*- coding: utf-8 -*-
from openerp import http

# class KhfProject(http.Controller):
#     @http.route('/khf_project/khf_project/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/khf_project/khf_project/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('khf_project.listing', {
#             'root': '/khf_project/khf_project',
#             'objects': http.request.env['khf_project.khf_project'].search([]),
#         })

#     @http.route('/khf_project/khf_project/objects/<model("khf_project.khf_project"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('khf_project.object', {
#             'object': obj
#         })