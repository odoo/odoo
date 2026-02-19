# -*- coding: utf-8 -*-
# from odoo import http


# class IziDataLibMysql(http.Controller):
#     @http.route('/izi_data_lib_web/izi_data_lib_web/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/izi_data_lib_web/izi_data_lib_web/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('izi_data_lib_web.listing', {
#             'root': '/izi_data_lib_web/izi_data_lib_web',
#             'objects': http.request.env['izi_data_lib_web.izi_data_lib_web'].search([]),
#         })

#     @http.route('/izi_data_lib_web/izi_data_lib_web/objects/<model("izi_data_lib_web.izi_data_lib_web"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('izi_data_lib_web.object', {
#             'object': obj
#         })
