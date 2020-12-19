# -*- coding: utf-8 -*-
# from odoo import http


# class CustomReport(http.Controller):
#     @http.route('/custom_report/custom_report/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_report/custom_report/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_report.listing', {
#             'root': '/custom_report/custom_report',
#             'objects': http.request.env['custom_report.custom_report'].search([]),
#         })

#     @http.route('/custom_report/custom_report/objects/<model("custom_report.custom_report"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_report.object', {
#             'object': obj
#         })
