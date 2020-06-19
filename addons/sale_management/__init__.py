# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers
from odoo.api import Environment, SUPERUSER_ID


def uninstall_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    res_ids = env['ir.model.data'].search([
        ('model', '=', 'ir.ui.menu'),
        ('module', '=', 'sale')
    ]).mapped('res_id')
    env['ir.ui.menu'].browse(res_ids).update({'active': False})


def post_init_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    res_ids = env['ir.model.data'].search([
        ('model', '=', 'ir.ui.menu'),
        ('module', '=', 'sale'),
    ]).mapped('res_id')
    env['ir.ui.menu'].browse(res_ids).update({'active': True})
