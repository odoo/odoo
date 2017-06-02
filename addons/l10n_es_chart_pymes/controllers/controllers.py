# -*- coding: utf-8 -*-
from odoo import http

# class L10nEsChartPymes(http.Controller):
#     @http.route('/l10n_es_chart_pymes/l10n_es_chart_pymes/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/l10n_es_chart_pymes/l10n_es_chart_pymes/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('l10n_es_chart_pymes.listing', {
#             'root': '/l10n_es_chart_pymes/l10n_es_chart_pymes',
#             'objects': http.request.env['l10n_es_chart_pymes.l10n_es_chart_pymes'].search([]),
#         })

#     @http.route('/l10n_es_chart_pymes/l10n_es_chart_pymes/objects/<model("l10n_es_chart_pymes.l10n_es_chart_pymes"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('l10n_es_chart_pymes.object', {
#             'object': obj
#         })