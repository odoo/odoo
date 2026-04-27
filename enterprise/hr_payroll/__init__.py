#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard
from . import report


def _auto_install_l10n_hr_payroll(env):
    """Installs l10n_**_hr_payroll modules automatically if such exists for the countries that companies are in"""
    country_codes = env['res.company'].search([]).country_id.mapped('code')
    if not country_codes:
        return
    possible_module_names = [
        f'l10n_{country_code.lower()}_hr_payroll'
        for country_code in country_codes
        if country_code != 'FR'
    ]
    modules = env['ir.module.module'].search([('name', 'in', possible_module_names), ('state', '=', 'uninstalled')])
    if modules:
        modules.sudo().button_install()


def _post_init_hook(env):
    env['res.company'].search([])._create_dashboard_notes()
    _auto_install_l10n_hr_payroll(env)
