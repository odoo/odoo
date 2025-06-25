# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import report


def _install_hr_localization(env):
    if env["res.company"].search_count([('partner_id.country_id.code', '=', 'MX')], limit=1):
        l10n_mx = env['ir.module.module'].sudo().search([
            ('name', '=', 'l10n_mx_hr'),
            ('state', 'not in', ['installed', 'to install', 'to upgrade']),
        ])
        if l10n_mx:
            l10n_mx.button_install()


def _set_administrator_email_for_empty_db(env):
    admin_user = env.ref('base.user_admin', raise_if_not_found=False)
    if not admin_user:
        return

    if env['res.users'].search_count([]) == 1:
        employee = env['hr.employee'].search([('user_id', '=', admin_user.id)], limit=1)
        if employee and not employee.work_email:
            employee.work_email = 'admin@example.com'


def _post_init_hook(env):
    _install_hr_localization(env)
    _set_administrator_email_for_empty_db(env)
