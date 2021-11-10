# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import demo
from . import wizard
from . import report
from . import populate

from odoo import api, SUPERUSER_ID

SYSCOHADA_LIST = ['BJ', 'BF', 'CM', 'CF', 'KM', 'CG', 'CI', 'GA', 'GN', 'GW', 'GQ', 'ML', 'NE', 'CD', 'SN', 'TD', 'TG']

def _set_fiscal_country(env):
    """ Sets the fiscal country on existing companies when installing the module.
    That field is an editable computed field. It doesn't automatically get computed
    on existing records by the ORM when installing the module, so doing that by hand
    ensures existing records will get a value for it if needed.
    """
    env['res.company'].search([]).compute_account_tax_fiscal_country()


def _auto_install_l10n(env):
    #check the country of the main company (only) and eventually load some module needed in that country
    country_code = env.company.country_id.code
    if country_code:
        #auto install localization module(s) if available
        to_install_l10n = env['ir.module.module'].search_count([
            ('category_id', '=', env.ref('base.module_category_accounting_localizations_account_charts').id),
            ('state', '=', 'to install'),
        ])
        module_list = []
        if to_install_l10n:
            # We don't install a CoA if one was passed in the command line
            # or has been selected to install
            pass
        elif country_code in SYSCOHADA_LIST:
            #countries using OHADA Chart of Accounts
            module_list.append('l10n_syscohada')
        elif country_code == 'GB':
            module_list.append('l10n_uk')
        elif country_code == 'DE':
            module_list.append('l10n_de_skr03')
            module_list.append('l10n_de_skr04')
        else:
            if env['ir.module.module'].search([('name', '=', 'l10n_' + country_code.lower())]):
                module_list.append('l10n_' + country_code.lower())
            else:
                module_list.append('l10n_generic_coa')
        if country_code in ['US', 'CA']:
            module_list.append('account_check_printing')
        if country_code in SYSCOHADA_LIST + [
            'AT', 'BE', 'CA', 'CO', 'DE', 'EC', 'ES', 'ET', 'FR', 'GR', 'IT', 'LU', 'MX', 'NL', 'NO',
            'PL', 'PT', 'RO', 'SI', 'TR', 'GB', 'VE', 'VN'
            ]:
            module_list.append('base_vat')
        if country_code == 'MX':
            module_list.append('l10n_mx_edi')
        if country_code == 'IT':
            module_list.append('l10n_it_edi_sdicoop')
        if country_code == 'SA':
            module_list.append('l10n_sa_invoice')

        module_ids = env['ir.module.module'].search([('name', 'in', module_list), ('state', '=', 'uninstalled')])
        module_ids.sudo().button_install()

def _account_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _auto_install_l10n(env)
    _set_fiscal_country(env)
