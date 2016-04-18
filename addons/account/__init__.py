# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import models

import wizard
import report
from openerp import SUPERUSER_ID, _
from openerp.exceptions import RedirectWarning
from openerp.modules.registry import RegistryManager


def _pre_install_check(cr):
    registry = RegistryManager.get(cr.dbname)
    # Done with SQL to avoid registry loading issues during an install
    cr.execute("""
        SELECT p.country_id
        FROM res_company c
        JOIN res_users u ON (c.id = u.company_id)
        JOIN res_partner p ON (p.id = c.partner_id)
        WHERE u.id = %s
    """, (SUPERUSER_ID,))
    country = cr.fetchone()[0]
    if not country:
        action = registry['ir.model.data'].xmlid_to_object(cr, SUPERUSER_ID, 'base.action_res_company_form')
        warning = _('The country on your company is not yet set. Please set it in order to configure your accounting according to your country.')
        raise RedirectWarning(warning, action.id, _('Configure your company data'))

def _auto_install_l10n(cr, registry):
    #check the country of the main company (only) and eventually load some module needed in that country
    country_code = registry['res.users'].browse(cr, SUPERUSER_ID, SUPERUSER_ID, {}).company_id.country_id.code
    if country_code:
        #auto install localization module(s) if available
        module_list = []
        if country_code in ['BJ', 'BF', 'CM', 'CF', 'KM', 'CG', 'CI', 'GA', 'GN', 'GW', 'GQ', 'ML', 'NE', 'CD', 'SN', 'TD', 'TG']:
            #countries using OHADA Chart of Accounts
            module_list.append('l10n_syscohada')
        elif country_code == 'GB':
            module_list.append('l10n_uk')
        else:
            if registry['ir.module.module'].search(cr, SUPERUSER_ID, [('name', '=', 'l10n_' + country_code.lower())]):
                module_list.append('l10n_' + country_code.lower())
            else:
                module_list.append('l10n_generic_coa')
        if country_code == 'US':
            module_list.append('account_plaid')
            module_list.append('account_check_printing')
        if country_code in ['US', 'AU', 'NZ', 'CA', 'CO', 'EC', 'ES', 'FR', 'IN', 'MX', 'UK']:
            module_list.append('account_yodlee')

        #european countries will be using SEPA
        europe = registry['ir.model.data'].xmlid_to_object(cr, SUPERUSER_ID, 'base.europe', raise_if_not_found=False, context={})
        if europe:
            europe_country_codes = [x.code for x in europe.country_ids]
            if country_code in europe_country_codes:
                module_list.append('account_sepa')
        module_ids = registry['ir.module.module'].search(cr, SUPERUSER_ID, [('name', 'in', module_list), ('state', '=', 'uninstalled')])
        registry['ir.module.module'].button_install(cr, SUPERUSER_ID, module_ids, {})
