# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from .models.iap import jsonrpc, charge, InsufficientCreditError

from odoo.api import Environment, SUPERUSER_ID

def _install_web_settings_dashboard(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    env['ir.module.module'].search([
        ('name', '=', 'web_settings_dashboard'),
        ('state', '=', 'uninstalled'),
    ]).button_install()
