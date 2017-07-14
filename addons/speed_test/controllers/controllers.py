# -*- coding: utf-8 -*-
from odoo import http

# class SpeedTest(http.Controller):
#     @http.route('/speed_test/speed_test/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/speed_test/speed_test/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('speed_test.listing', {
#             'root': '/speed_test/speed_test',
#             'objects': http.request.env['speed_test.speed_test'].search([]),
#         })

#     @http.route('/speed_test/speed_test/objects/<model("speed_test.speed_test"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('speed_test.object', {
#             'object': obj
#         })