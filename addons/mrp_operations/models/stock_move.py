# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models


class StockMove(models.Model):

    _inherit = 'stock.move'
    move_dest_id_lines = fields.One2many('stock.move', 'move_dest_id', 'Children Moves')
