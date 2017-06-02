# -*- coding: utf-8 -*-
from odoo import http

# class L10nEsChartAssoc(http.Controller):
#     @http.route('/l10n_es_chart_assoc/l10n_es_chart_assoc/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/l10n_es_chart_assoc/l10n_es_chart_assoc/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('l10n_es_chart_assoc.listing', {
#             'root': '/l10n_es_chart_assoc/l10n_es_chart_assoc',
#             'objects': http.request.env['l10n_es_chart_assoc.l10n_es_chart_assoc'].search([]),
#         })

#     @http.route('/l10n_es_chart_assoc/l10n_es_chart_assoc/objects/<model("l10n_es_chart_assoc.l10n_es_chart_assoc"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('l10n_es_chart_assoc.object', {
#             'object': obj
#         })