# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import demo
from . import models
from . import wizard

from odoo import Command

import logging

_logger = logging.getLogger(__name__)


def _account_accountant_post_init(env):
    country_code = env.company.country_id.code
    if country_code:
        module_list = []

        # SEPA zone countries will be using SEPA
        sepa_zone = env.ref('base.sepa_zone', raise_if_not_found=False)
        sepa_zone_country_codes = sepa_zone and sepa_zone.mapped('country_ids.code') or []

        if country_code in sepa_zone_country_codes:
            module_list.extend(['account_iso20022', 'account_bank_statement_import_camt'])

        module_ids = env['ir.module.module'].search([('name', 'in', module_list), ('state', '=', 'uninstalled')])
        if module_ids:
            module_ids.sudo().button_install()

    for company in env['res.company'].search([('chart_template', '!=', False)], order="parent_path"):
        ChartTemplate = env['account.chart.template'].with_company(company)
        ChartTemplate._load_data({
            'res.company': ChartTemplate._get_account_accountant_res_company(company.chart_template),
        })


def uninstall_hook(env):
    # Disable the basic group to remove access menus defined in account
    group_basic = env.ref('account.group_account_basic')
    group_manager = env.ref('account.group_account_manager')
    if group_basic:
        group_basic.write({
            'users': [Command.clear()],
            'category_id': env.ref("base.module_category_hidden").id,
        })
        group_manager.write({
            'implied_ids': [Command.unlink(group_basic.id)],
        })
