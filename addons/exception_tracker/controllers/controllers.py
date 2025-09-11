# -*- coding: utf-8 -*-
# from odoo import http


# class ExceptionTracker(http.Controller):
#     @http.route('/exception_tracker/exception_tracker', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/exception_tracker/exception_tracker/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('exception_tracker.listing', {
#             'root': '/exception_tracker/exception_tracker',
#             'objects': http.request.env['exception_tracker.exception_tracker'].search([]),
#         })

#     @http.route('/exception_tracker/exception_tracker/objects/<model("exception_tracker.exception_tracker"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('exception_tracker.object', {
#             'object': obj
#         })
