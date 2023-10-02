# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import demo

from odoo import api, SUPERUSER_ID


def init_settings(env):
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


def post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    init_settings(env)
