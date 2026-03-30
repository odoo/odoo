# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import tools

from odoo import api, SUPERUSER_ID


def _l10n_it_edi_update_export_tax(env):
    chart_template = env.ref('l10n_it.l10n_it_chart_template_generic', raise_if_not_found=False)
    if chart_template:
        for company in env['res.company'].search([('chart_template_id', '=', chart_template.id)]):
            tax = env.ref(f'l10n_it.{company.id}_00eu', raise_if_not_found=False)
            if tax:
                tax.write({
                    'l10n_it_has_exoneration': True,
                    'l10n_it_kind_exoneration': 'N3.2',
                    'l10n_it_law_reference': 'Art. 41, DL n. 331/93',
                })
            service_tax = env.ref(f'l10n_it.{company.id}_00eus', raise_if_not_found=False)
            if service_tax:
                service_tax.write({
                    'l10n_it_has_exoneration': True,
                    'l10n_it_kind_exoneration': 'N3.2',
                    'l10n_it_law_reference': 'Art. 7ter, DPR 633/1972',
                })


def _l10n_it_edi_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _l10n_it_edi_update_export_tax(env)
