# -*- coding: utf-8 -*-
from openerp import http

# class WebsiteJqueryValidation(http.Controller):
#     @http.route('/website_jquery_validation/website_jquery_validation/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/website_jquery_validation/website_jquery_validation/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('website_jquery_validation.listing', {
#             'root': '/website_jquery_validation/website_jquery_validation',
#             'objects': http.request.env['website_jquery_validation.website_jquery_validation'].search([]),
#         })

#     @http.route('/website_jquery_validation/website_jquery_validation/objects/<model("website_jquery_validation.website_jquery_validation"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('website_jquery_validation.object', {
#             'object': obj
#         })