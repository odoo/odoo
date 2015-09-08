# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import models

import wizard
import report
from openerp import SUPERUSER_ID

def _auto_install_l10n(cr, registry):
    #check the country of the main company (only) and eventually load some module needed in that country
    country_code = registry['res.users'].browse(cr, SUPERUSER_ID, SUPERUSER_ID, {}).company_id.country_id.code
    if country_code:
        #auto install localization module(s) if available
        module_list = []
        if country_code in ['BJ', 'BF', 'CM', 'CF', 'KM', 'CG', 'CI', 'GA', 'GN', 'GW', 'GQ', 'ML', 'NE', 'CD', 'SN', 'TD', 'TG']:
            #countries using OHADA Chart of Accounts
            module_list.append('l10n_syscohada')
        else:
            module_list.append('l10n_' + country_code.lower())
        if country_code == 'US':
            module_list.append('account_plaid')
        if country_code in ['US', 'AU', 'NZ']:
            module_list.append('account_yodlee')

        module_ids = registry['ir.module.module'].search(cr, SUPERUSER_ID, [('name', 'in', module_list), ('state', '=', 'uninstalled')])
        registry['ir.module.module'].button_install(cr, SUPERUSER_ID, module_ids, {})

