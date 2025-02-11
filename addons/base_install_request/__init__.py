# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from odoo import tools


def _auto_install_apps(env):
    if not tools.config.get('default_productivity_apps', False):
        return
    env['ir.module.module'].sudo().search([
        ('name', 'in', [
            # Community
            'hr', 'mass_mailing', 'project', 'survey',
            # Enterprise
            'appointment', 'knowledge', 'planning', 'sign',
        ]),
        ('state', '=', 'uninstalled')
    ]).button_install()
