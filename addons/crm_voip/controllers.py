# -*- coding: utf-8 -*-
from openerp import http

# class Crmvoip(http.Controller):
#     @http.route('/crm_voip/crm_voip/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/crm_voip/crm_voip/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('crm_voip.listing', {
#             'root': '/crm_voip/crm_voip',
#             'objects': http.request.env['crm_voip.crm_voip'].search([]),
#         })

#     @http.route('/crm_voip/crm_voip/objects/<model("crm_voip.crm_voip"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('crm_voip.object', {
#             'object': obj
#         })