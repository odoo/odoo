# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from odoo import api, SUPERUSER_ID


def _l10n_it_edi_withholding_add_taxes(env):
    chart_template = env.ref('l10n_it.l10n_it_chart_template_generic', raise_if_not_found=False)
    if chart_template:
        for company in env['res.company'].search([('chart_template_id', '=', chart_template.id)]):
            # Create the new taxes on existing company
            cid = company.id
            existing_taxes = no_tax = env['account.tax']
            templates = env['account.tax.template']
            for xml_id in (
                '20awi', '20vwi',
                '20awc', '20vwc',
                '23awo', '23vwo',
                '4vcp', '4acp',
                '4vinps', '4ainps'
            ):
                templates |= env.ref(f"l10n_it_edi_withholding.{xml_id}")
                tax = env.ref(f"l10n_it_edi_withholding.{cid}_{xml_id}", raise_if_not_found=False) or no_tax
                existing_taxes |= tax
            if not existing_taxes:
                templates._generate_tax(company)
            # Increase the sequence number of the old taxes by adding 20
            # so that the withholding can have sequence=10 and the pension fund sequence=20
            all_taxes = env['account.tax'].search([('company_id', '=', company.id)])
            if all_taxes.filtered(lambda x: (x.sequence <= 20 and not x.l10n_it_pension_fund_type and not x.l10n_it_withholding_type)):
                for tax in all_taxes:
                    if not tax.l10n_it_withholding_type and not tax.l10n_it_pension_fund_type:
                        tax.sequence += 21

def _l10n_it_edi_withholding_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _l10n_it_edi_withholding_add_taxes(env)
