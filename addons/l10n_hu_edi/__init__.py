# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import demo

from odoo import api, SUPERUSER_ID


def _init_hungarian_company(env):
    """If the company is localized in Hungary, activate the cash rounding by default."""
    # The cash rounding is activated by default only if the company is localized in Hungary.
    for company in env["res.company"].search([("partner_id.country_id.code", "=", "HU")]):
        res_config_id = env["res.config.settings"].create(
            {
                "company_id": company.id,
                "group_cash_rounding": True,
                "tax_calculation_rounding_method": "round_globally",
            }
        )
        # We need to call execute, otherwise the "implied_group" in fields are not processed.
        res_config_id.execute()


def _update_hungarian_fields_on_taxes(env):
    """Update the tax identification fields"""
    chart_template = env.ref("l10n_hu.hungarian_chart_template", raise_if_not_found=False)
    if chart_template:
        companies = env["res.company"].search([("chart_template_id", "=", chart_template.id)])
        tax_templates = env["account.tax.template"].search(
            [
                ("chart_template_id", "=", chart_template.id),
                ("l10n_hu_tax_type", "!=", False),
            ]
        )
        xml_ids = tax_templates.get_external_id()
        for company in companies:
            for tax_template in tax_templates:
                module, xml_id = xml_ids[tax_template.id].split(".")
                tax = env.ref(f"{module}.{company.id}_{xml_id}", raise_if_not_found=False)
                if tax:
                    tax.write(
                        {
                            "l10n_hu_tax_type": tax_template.l10n_hu_tax_type,
                            "l10n_hu_tax_reason": tax_template.l10n_hu_tax_reason,
                        }
                    )


def post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _init_hungarian_company(env)
    _update_hungarian_fields_on_taxes(env)
