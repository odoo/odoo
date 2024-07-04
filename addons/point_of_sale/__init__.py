# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from . import models
from . import controllers
from . import report
from . import wizard


def uninstall_hook(env):
    #The search domain is based on how the sequence is defined in the _get_sequence_values method in /addons/point_of_sale/models/stock_warehouse.py
    env['ir.sequence'].search([('name', 'ilike', '%Picking POS%'), ('prefix', 'ilike', '%/POS/%')]).unlink()
    pickings = env['stock.picking'].search([('pos_session_id', '!=', False)])
    for picking in pickings:
        picking.name = picking.name + _('(Deleted POS Session)')
