# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

SYSCOHADA_LIST = ['BJ', 'BF', 'CM', 'CF', 'KM', 'CG', 'CI', 'GA', 'GN', 'GW', 'GQ', 'ML', 'NE',
                  'CD', 'SN', 'TD', 'TG']
VAT_LIST = ['AT', 'BE', 'CA', 'CO', 'DE', 'EC', 'ES', 'ET', 'FR', 'GR', 'IT', 'LU', 'MX', 'NL',
            'NO', 'PL', 'PT', 'RO', 'SI', 'TR', 'GB', 'VE', 'VN']

def _set_fiscal_country(env):
    """ Sets the fiscal country on existing companies when installing the module.
    That field is an editable computed field. It doesn't automatically get computed
    on existing records by the ORM when installing the module, so doing that by hand
    ensures existing records will get a value for it if needed.
    """
    env['res.company'].search([]).compute_account_tax_fiscal_country()


def _auto_install_l10n(env):
    # Check the country of the main company (only) and eventually load some module needed in that country
    country = env.company.country_id
    country_code = country.code
    if country_code:
        module_list = []
<<<<<<< 17.0
        if not env.company.chart_template:
            template_code = env['account.chart.template']._guess_chart_template(country)
            module_list.append(env['account.chart.template']._get_chart_template_mapping()[template_code]['module'])
        if country_code in ['US', 'CA']:
            module_list.append('account_check_printing')
        if country_code in SYSCOHADA_LIST + VAT_LIST:
||||||| 8346b2a7561c178fd7e9f9d1fbd7dac3e3843fd1
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
        if country_code in SYSCOHADA_LIST + [
            'AT', 'BE', 'CA', 'CO', 'DE', 'EC', 'ES', 'ET', 'FR', 'GR', 'IT', 'LU', 'MX', 'NL', 'NO',
            'PL', 'PT', 'RO', 'SI', 'TR', 'GB', 'VE', 'VN'
            ]:
=======
        if to_install_l10n:
            # We don't install a CoA if one was passed in the command line
            # or has been selected to install
            pass
        elif country_code in SYSCOHADA_LIST:
            #countries using OHADA Chart of Accounts
            module_list.append('l10n_syscohada')
        elif country_code == 'GB':
            module_list.extend(('l10n_uk', 'account_bacs'))
        elif country_code == 'DE':
            module_list.append('l10n_de_skr03')
            module_list.append('l10n_de_skr04')
        else:
            if env['ir.module.module'].search([('name', '=', 'l10n_' + country_code.lower())]):
                module_list.append('l10n_' + country_code.lower())
            else:
                module_list.append('l10n_generic_coa')
        if country_code in SYSCOHADA_LIST + [
            'AT', 'BE', 'CA', 'CO', 'DE', 'EC', 'ES', 'ET', 'FR', 'GR', 'IT', 'LU', 'MX', 'NL', 'NO',
            'PL', 'PT', 'RO', 'SI', 'TR', 'GB', 'VE', 'VN'
            ]:
>>>>>>> d18a338c8d1a82079ee19e81b975fde6c5c083f1
            module_list.append('base_vat')

        module_ids = env['ir.module.module'].search([('name', 'in', module_list), ('state', '=', 'uninstalled')])
        if module_ids:
            module_ids.sudo().button_install()

def _auto_install_avatax(env):
    """ Install the avatax module automatically if the company is in a country that uses avatax """
    avatax_country_codes = ['US', 'CA']

    country = env.company.country_id
    country_code = country.code

    if country_code in avatax_country_codes:
        module = env['ir.module.module'].search([('name', '=', 'account_avatax')])
        if module.state == 'uninstalled':
            module.sudo().button_install()

def _account_post_init(env):
    _auto_install_l10n(env)
    _set_fiscal_country(env)
    _auto_install_avatax(env)

# imported here to avoid dependency cycle issues
# pylint: disable=wrong-import-position
from . import controllers
from . import models
from . import demo
from . import wizard
from . import report
from . import populate
from . import tools
