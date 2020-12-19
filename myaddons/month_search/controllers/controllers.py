# -*- coding: utf-8 -*-
# from odoo import http


# class MonthSearch(http.Controller):
#     @http.route('/month_search/month_search/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/month_search/month_search/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('month_search.listing', {
#             'root': '/month_search/month_search',
#             'objects': http.request.env['month_search.month_search'].search([]),
#         })

#     @http.route('/month_search/month_search/objects/<model("month_search.month_search"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('month_search.object', {
#             'object': obj
#         })
