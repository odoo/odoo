# -*- coding: utf-8 -*-
from odoo import http

# class Supercomputer(http.Controller):
#     @http.route('/supercomputer/supercomputer/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/supercomputer/supercomputer/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('supercomputer.listing', {
#             'root': '/supercomputer/supercomputer',
#             'objects': http.request.env['supercomputer.supercomputer'].search([]),
#         })

#     @http.route('/supercomputer/supercomputer/objects/<model("supercomputer.supercomputer"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('supercomputer.object', {
#             'object': obj
#         })