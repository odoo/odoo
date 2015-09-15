# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'move_dest_id_lines': fields.one2many('stock.move', 'move_dest_id', 'Children Moves')
    }
