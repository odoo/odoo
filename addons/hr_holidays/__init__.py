# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import populate
from . import report
from . import wizard

from odoo import api, SUPERUSER_ID


def _auto_install_l10n_hr_holidays(env):
    country_codes = env['res.company'].search([]).mapped('country_id.code')
    if not country_codes:
        return
    possible_module_names = [f'l10n_{country_code.lower()}_hr_holidays' for country_code in country_codes]
    modules = env['ir.module.module'].search([('name', 'in', possible_module_names), ('state', '=', 'uninstalled')])
    if modules:
        modules.sudo().button_install()


def _hr_holiday_post_init(env):
    _auto_install_l10n_hr_holidays(env)
