# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import receipt
from . import models
from . import report
from . import controllers
from . import wizard


def uninstall_hook(env):
    #The search domain is based on how the sequence is defined in the _get_sequence_values method in /addons/point_of_sale/models/stock_warehouse.py
    env['ir.sequence'].search([('name', 'ilike', '%Picking POS%'), ('prefix', 'ilike', '%/POS/%')]).unlink()

def post_init_hook(env):
    # Updates qty_max to qty_free during initialization to avoid breaking the constraint.
    combos = env['product.combo'].search([]).sudo()
    for combo in combos:
        combo.qty_max = combo.qty_free
