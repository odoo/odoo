# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

def _set_fiscal_country(env):
    """ Sets the fiscal country on existing companies when installing the module.
    That field is an editable computed field. It doesn't automatically get computed
    on existing records by the ORM when installing the module, so doing that by hand
    ensures existing records will get a value for it if needed.
    """
    env['res.company'].search([]).compute_account_tax_fiscal_country()


<<<<<<< saas-17.2
||||||| 8a4b56fb1de80f701d8cd2d88d6f330814ea46b5
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

=======
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
        if country_code == 'MC':
            module_list.append('l10n_fr')

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

>>>>>>> 1a3ca0063eaeb3a1baa95576ce73116c75438874
def _account_post_init(env):
    _set_fiscal_country(env)

# imported here to avoid dependency cycle issues
# pylint: disable=wrong-import-position
from . import controllers
from . import models
from . import demo
from . import wizard
from . import report
from . import populate
from . import tools
