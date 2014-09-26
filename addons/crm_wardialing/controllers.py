# -*- coding: utf-8 -*-
from openerp import http

# class CrmWardialing(http.Controller):
#     @http.route('/crm_wardialing/crm_wardialing/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/crm_wardialing/crm_wardialing/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('crm_wardialing.listing', {
#             'root': '/crm_wardialing/crm_wardialing',
#             'objects': http.request.env['crm_wardialing.crm_wardialing'].search([]),
#         })

#     @http.route('/crm_wardialing/crm_wardialing/objects/<model("crm_wardialing.crm_wardialing"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('crm_wardialing.object', {
#             'object': obj
#         })