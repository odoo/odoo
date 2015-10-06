# -*- coding: utf-8 -*-
from openerp import http

# class WebsiteDataValidate(http.Controller):
#     @http.route('/website_data_validate/website_data_validate/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/website_data_validate/website_data_validate/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('website_data_validate.listing', {
#             'root': '/website_data_validate/website_data_validate',
#             'objects': http.request.env['website_data_validate.website_data_validate'].search([]),
#         })

#     @http.route('/website_data_validate/website_data_validate/objects/<model("website_data_validate.website_data_validate"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('website_data_validate.object', {
#             'object': obj
#         })