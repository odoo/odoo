# -*- coding: utf-8 -*-
# from odoo import http


# class School(http.Controller):
#     @http.route('/school/school', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/school/school/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('school.listing', {
#             'root': '/school/school',
#             'objects': http.request.env['school.school'].search([]),
#         })

#     @http.route('/school/school/objects/<model("school.school"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('school.object', {
#             'object': obj
#         })

