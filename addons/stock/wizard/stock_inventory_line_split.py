# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
from service import web_services
from tools.misc import UpdateableStr, UpdateableDict
from tools.translate import _
import netsvc
import pooler
import time
import wizard

class stock_inventory_line_split(osv.osv_memory):
    _name = "stock.inventory.line.split"
    _description = "Split inventory lines"
    _columns = {
            'prefix': fields.char('Prefix', size=64), 
            'quantity': fields.float('Quantity per lot'), 
            }

    def _check_production_lot(self, cr, uid, context):
        stock_inventory_line_obj = self.pool.get('stock.inventory.line')
        for inv_obj in stock_inventory_line_obj.browse(cr, uid, \
                            context['active_ids']):
            if not inv_obj.prod_lot_id:
                raise osv.except_osv(_('Caution!'), _('Before splitting the \
inventory lines, make sure the production lot is assigned to this product.'))
            return

    _defaults = {
            'quantity': lambda *a: '1', 
            'prefix': _check_production_lot, 
            }

    def split_lines(self, cr, uid, ids, context):
        inv_id = context['active_id']
        inv_line_obj = self.pool.get('stock.inventory.line')
        prodlot_obj = self.pool.get('stock.production.lot')
        
        ir_sequence_obj = self.pool.get('ir.sequence')
        sequence = ir_sequence_obj.get(cr, uid, 'stock.lot.serial')
        if not sequence:
            raise wizard.except_wizard(_('Error!'), _('No production sequence defined'))

        for linesplit_obj in self.browse(cr, uid, ids):

            if linesplit_obj.prefix:
                sequence = linesplit_obj.prefix + '/' + (sequence or '')

            inv = inv_line_obj.browse(cr, uid, [inv_id])[0]
            quantity = linesplit_obj.quantity
            prodlot_obj.write(cr, uid, inv.prod_lot_id.id, {'name': sequence})

            if quantity <= 0 or inv.product_qty == 0:
                return {}

            quantity_rest = inv.product_qty % quantity

            update_val = {
                    'product_qty': quantity, 
            }

            new_line = []
            for idx in range(int(inv.product_qty // quantity)):
                if idx:
                    current_line = inv_line_obj.copy(cr, uid, inv.id, 
                                 {'prod_lot_id': inv.prod_lot_id.id})
                    new_line.append(current_line)
                else:
                    current_line = inv.id
                    inv_line_obj.write(cr, uid, [current_line], update_val)

            if quantity_rest > 0:
                idx = int(inv.product_qty // quantity)
                update_val['product_qty'] = quantity_rest

                if idx:
                    current_line = inv_line_obj.copy(cr, uid, inv.id, 
                                 {'prod_lot_id': inv.prod_lot_id.id})
                    new_line.append(current_line)
                else:
                    current_line = inv_line_obj.id
                inv_line_obj.write(cr, uid, [current_line], update_val)

            return {}

stock_inventory_line_split()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

