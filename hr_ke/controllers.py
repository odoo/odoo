# -*- coding: utf-8 -*-
from openerp import http

# class HrKe(http.Controller):
#     @http.route('/hr_ke/hr_ke/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_ke/hr_ke/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_ke.listing', {
#             'root': '/hr_ke/hr_ke',
#             'objects': http.request.env['hr_ke.hr_ke'].search([]),
#         })

#     @http.route('/hr_ke/hr_ke/objects/<model("hr_ke.hr_ke"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_ke.object', {
#             'object': obj
#         })