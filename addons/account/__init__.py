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
        if not env.company.chart_template:
            template_code = env['account.chart.template']._guess_chart_template(country)
            module_list.append(env['account.chart.template']._get_chart_template_mapping()[template_code]['module'])
        if country_code in ['US', 'CA']:
            module_list.append('account_check_printing')
        if country_code in SYSCOHADA_LIST + VAT_LIST:
            module_list.append('base_vat')
        if country_code == 'uk':
            module_list.append('account_bacs')

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
