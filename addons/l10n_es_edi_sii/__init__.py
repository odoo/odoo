# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models
from odoo import api, SUPERUSER_ID


def _l10n_es_edi_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env['res.company'].search([('partner_id.country_id.code', '=', 'ES')])

    all_chart_templates = companies.chart_template_id
    current_chart_template = all_chart_templates
    while current_chart_template.parent_id:
        all_chart_templates |= current_chart_template.parent_id
        current_chart_template = current_chart_template.parent_id

    if all_chart_templates:
        tax_templates = env['account.tax.template'].search([
            ('chart_template_id', 'in', all_chart_templates.ids),
            '|', '|', '|',
            ('l10n_es_type', '!=', False),
            ('l10n_es_exempt_reason', '!=', False),
            ('tax_scope', '!=', False),
            ('l10n_es_bien_inversion', '!=', False),
        ])
        xml_ids = tax_templates.get_external_id()
        for company in companies:
            for tax_template in tax_templates:
                module, xml_id = xml_ids.get(tax_template.id).split('.')
                tax = env.ref('%s.%s_%s' % (module, company.id, xml_id), raise_if_not_found=False)
                if tax:
                    tax.write({
                        'l10n_es_exempt_reason': tax_template.l10n_es_exempt_reason,
                        'tax_scope': tax_template.tax_scope,
                        'l10n_es_type': tax_template.l10n_es_type,
                        'l10n_es_bien_inversion': tax_template.l10n_es_bien_inversion,
                    })
