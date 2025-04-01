# -*- coding: utf-8 -*-
# from odoo import http


# class SalesRouteManagement(http.Controller):
#     @http.route('/sales_route_management/sales_route_management', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sales_route_management/sales_route_management/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sales_route_management.listing', {
#             'root': '/sales_route_management/sales_route_management',
#             'objects': http.request.env['sales_route_management.sales_route_management'].search([]),
#         })

#     @http.route('/sales_route_management/sales_route_management/objects/<model("sales_route_management.sales_route_management"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sales_route_management.object', {
#             'object': obj
#         })
