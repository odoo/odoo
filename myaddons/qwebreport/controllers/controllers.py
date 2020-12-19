# -*- coding: utf-8 -*-
# from odoo import http


# class Qwebreport(http.Controller):
#     @http.route('/qwebreport/qwebreport/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/qwebreport/qwebreport/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('qwebreport.listing', {
#             'root': '/qwebreport/qwebreport',
#             'objects': http.request.env['qwebreport.qwebreport'].search([]),
#         })

#     @http.route('/qwebreport/qwebreport/objects/<model("qwebreport.qwebreport"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('qwebreport.object', {
#             'object': obj
#         })
