# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models
from odoo import api, SUPERUSER_ID


def _l10n_es_edi_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([('partner_id.country_id.code', '=', 'ES')]):
        taxes_data = env['account.chart.template']._get_data(company.chart_template, company, 'account.tax')
        for xml_id, tax_data in taxes_data.items():
            tax = env.ref('account.%s' % xml_id, raise_if_not_found=False)
            if tax:
                tax.write({
                    'l10n_es_exempt_reason': tax_data['l10n_es_exempt_reason'],
                    'tax_scope': tax_data['tax_scope'],
                    'l10n_es_type': tax_data['l10n_es_type'],
                })
