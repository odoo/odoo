# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers
from odoo.api import Environment, SUPERUSER_ID
from odoo.tools import column_exists, create_column


def pre_init_hook(cr):
    """Do not compute the sale_order_template_id field on existing SOs."""
    if not column_exists(cr, "sale_order", "sale_order_template_id"):
        create_column(cr, "sale_order", "sale_order_template_id", "int4")

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
