# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, SUPERUSER_ID

from . import models
from . import wizard
from . import populate


def _install_hr_localization(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    if any(c.partner_id.country_id.code == 'MX' for c in env['res.company'].search([])):
        l10n_mx = env['ir.module.module'].sudo().search([
            ('name', '=', 'l10n_mx_hr'),
            ('state', 'not in', ['installed', 'to install', 'to upgrade']),
        ])
        if l10n_mx:
            l10n_mx.button_install()
