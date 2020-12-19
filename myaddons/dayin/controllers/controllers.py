# -*- coding: utf-8 -*-
# from odoo import http


# class Dayin(http.Controller):
#     @http.route('/dayin/dayin/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/dayin/dayin/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('dayin.listing', {
#             'root': '/dayin/dayin',
#             'objects': http.request.env['dayin.dayin'].search([]),
#         })

#     @http.route('/dayin/dayin/objects/<model("dayin.dayin"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('dayin.object', {
#             'object': obj
#         })
