# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers
from . import report
from . import wizard


def uninstall_hook(env):
    warehouses = env['stock.warehouse'].sudo().search([('pos_type_id', '!=', False)])
    for warehouse in warehouses:
        sequence_data = warehouse._get_sequence_values()
        if sequence_data and sequence_data.get('pos_type_id'):
            env['ir.sequence'].sudo().search([('prefix', '=', sequence_data['pos_type_id']['prefix'])]).unlink()
