# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import tools


def _l10n_it_edi_update_export_tax(env):
    for company in env['res.company'].search([('chart_template', '=', 'it')]):
        tax = env.ref(f'l10n_it.{company.id}_00eu', raise_if_not_found=False)
        if tax:
            tax.write({
                'l10n_it_has_exoneration': True,
                'l10n_it_kind_exoneration': 'N3.2',
                'l10n_it_law_reference': 'Art. 41, DL n. 331/93',
            })


def _l10n_it_edi_post_init(env):
    _l10n_it_edi_update_export_tax(env)
