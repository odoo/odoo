# -*- coding: utf-8 -*-
# from odoo import http


# class RecursosHumanos(http.Controller):
#     @http.route('/recursos_humanos/recursos_humanos', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/recursos_humanos/recursos_humanos/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('recursos_humanos.listing', {
#             'root': '/recursos_humanos/recursos_humanos',
#             'objects': http.request.env['recursos_humanos.recursos_humanos'].search([]),
#         })

#     @http.route('/recursos_humanos/recursos_humanos/objects/<model("recursos_humanos.recursos_humanos"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('recursos_humanos.object', {
#             'object': obj
#         })

