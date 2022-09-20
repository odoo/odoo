# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from odoo import api, tools, SUPERUSER_ID


def _auto_install_apps(cr, registry):
    if not tools.config.get('default_productivity_apps', True):
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.module.module'].sudo().search([
        ('name', 'in', [
            # Community
            'hr', 'mass_mailing', 'project', 'survey',
            # Enterprise
            'appointment', 'knowledge', 'planning', 'sign',
        ]),
        ('state', '=', 'uninstalled')
    ]).button_install()
