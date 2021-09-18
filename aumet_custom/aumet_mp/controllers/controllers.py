# -*- coding: utf-8 -*-
# from odoo import http


# class AumetMp(http.Controller):
#     @http.route('/aumet_mp/aumet_mp/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/aumet_mp/aumet_mp/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('aumet_mp.listing', {
#             'root': '/aumet_mp/aumet_mp',
#             'objects': http.request.env['aumet_mp.aumet_mp'].search([]),
#         })

#     @http.route('/aumet_mp/aumet_mp/objects/<model("aumet_mp.aumet_mp"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('aumet_mp.object', {
#             'object': obj
#         })
