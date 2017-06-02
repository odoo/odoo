# -*- coding: utf-8 -*-
from odoo import http

# class L10nEsChartFull(http.Controller):
#     @http.route('/l10n_es_chart_full/l10n_es_chart_full/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/l10n_es_chart_full/l10n_es_chart_full/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('l10n_es_chart_full.listing', {
#             'root': '/l10n_es_chart_full/l10n_es_chart_full',
#             'objects': http.request.env['l10n_es_chart_full.l10n_es_chart_full'].search([]),
#         })

#     @http.route('/l10n_es_chart_full/l10n_es_chart_full/objects/<model("l10n_es_chart_full.l10n_es_chart_full"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('l10n_es_chart_full.object', {
#             'object': obj
#         })