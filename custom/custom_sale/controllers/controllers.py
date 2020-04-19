# -*- coding: utf-8 -*-
# from odoo import http


# class Custom(http.Controller):
#     @http.route('/custom/custom_sale/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom/custom_sale/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom.listing', {
#             'root': '/custom/custom_sale',
#             'objects': http.request.env['custom.custom'].search([]),
#         })

#     @http.route('/custom/custom_sale/objects/<model("custom.custom"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom.object', {
#             'object': obj
#         })
