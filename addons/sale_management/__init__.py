# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers
from odoo.tools.sql import column_exists, create_column


def pre_init_hook(env):
    """Do not compute the sale_order_template_id field on existing SOs."""
    if not column_exists(env.cr, "sale_order", "sale_order_template_id"):
        create_column(env.cr, "sale_order", "sale_order_template_id", "int4")

def uninstall_hook(env):
    res_ids = env['ir.model.data'].search([
        ('model', '=', 'ir.ui.menu'),
        ('module', '=', 'sale')
    ]).mapped('res_id')
    env['ir.ui.menu'].browse(res_ids).update({'active': False})


def post_init_hook(env):
    res_ids = env['ir.model.data'].search([
        ('model', '=', 'ir.ui.menu'),
        ('module', '=', 'sale'),
    ]).mapped('res_id')
    env['ir.ui.menu'].browse(res_ids).update({'active': True})
