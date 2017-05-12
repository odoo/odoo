# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import models

import wizard
import report

from odoo import api, SUPERUSER_ID


def _auto_install_l10n(cr, registry):
    #check the country of the main company (only) and eventually load some module needed in that country
    env = api.Environment(cr, SUPERUSER_ID, {})
    country_code = env.user.company_id.country_id.code
    if country_code:
        #auto install localization module(s) if available
        module_list = []
        if country_code in ['BJ', 'BF', 'CM', 'CF', 'KM', 'CG', 'CI', 'GA', 'GN', 'GW', 'GQ', 'ML', 'NE', 'CD', 'SN', 'TD', 'TG']:
            #countries using OHADA Chart of Accounts
            module_list.append('l10n_syscohada')
        elif country_code == 'GB':
            module_list.append('l10n_uk')
        else:
            if env['ir.module.module'].search([('name', '=', 'l10n_' + country_code.lower())]):
                module_list.append('l10n_' + country_code.lower())
            else:
                module_list.append('l10n_generic_coa')
        if country_code == 'US':
            module_list.append('account_plaid')
            module_list.append('account_check_printing')
        if country_code in ['US', 'AU', 'NZ', 'CA', 'CO', 'EC', 'ES', 'FR', 'IN', 'MX', 'UK']:
            module_list.append('account_yodlee')

        #european countries will be using SEPA
        europe = env.ref('base.europe', raise_if_not_found=False)
        if europe:
            europe_country_codes = [x.code for x in europe.country_ids]
            if country_code in europe_country_codes:
                module_list.append('account_sepa')
        module_ids = env['ir.module.module'].search([('name', 'in', module_list), ('state', '=', 'uninstalled')])
        module_ids.sudo().button_install()
