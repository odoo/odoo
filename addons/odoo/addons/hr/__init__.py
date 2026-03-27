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
