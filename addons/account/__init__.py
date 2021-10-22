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
    env.company.try_loading_coa(env.company._guess_chart_of_account())
    country_code = env.company.country_id.code
    if country_code:
        module_list = []
        if country_code in ['US', 'CA']:
            module_list.append('account_check_printing')
        if country_code in SYSCOHADA_LIST + [
            'AT', 'BE', 'CA', 'CO', 'DE', 'EC', 'ES', 'ET', 'FR', 'GR', 'IT', 'LU', 'MX', 'NL', 'NO',
            'PL', 'PT', 'RO', 'SI', 'TR', 'GB', 'VE', 'VN'
            ]:
            module_list.append('base_vat')

        module_ids = env['ir.module.module'].search([('name', 'in', module_list), ('state', '=', 'uninstalled')])
        module_ids.sudo().button_install()

def _account_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _auto_install_l10n(env)
    _set_fiscal_country(env)
