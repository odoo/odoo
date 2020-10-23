# -*- coding: utf-8 -*-
# from odoo import http


# class L10nDePosCert(http.Controller):
#     @http.route('/l10n_de_pos_cert/l10n_de_pos_cert/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/l10n_de_pos_cert/l10n_de_pos_cert/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('l10n_de_pos_cert.listing', {
#             'root': '/l10n_de_pos_cert/l10n_de_pos_cert',
#             'objects': http.request.env['l10n_de_pos_cert.l10n_de_pos_cert'].search([]),
#         })

#     @http.route('/l10n_de_pos_cert/l10n_de_pos_cert/objects/<model("l10n_de_pos_cert.l10n_de_pos_cert"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('l10n_de_pos_cert.object', {
#             'object': obj
#         })
