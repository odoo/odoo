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
from tools.translate import _
import time


class stock_partial_move_memory(osv.osv_memory):
    _name = "stock.move.memory"
    _rec_name = 'product_id'
    _columns = {
        'product_id' : fields.many2one('product.product', string="Product", required=True, readonly=True),
        'quantity' : fields.float("Quantity", required=True),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure', required=True, readonly=True),
        'prodlot_id' : fields.many2one('stock.production.lot', 'Production Lot'),
        'move_id' : fields.many2one('stock.move', "Move"),
        'wizard_id' : fields.many2one('stock.partial.move', string="Wizard"),
        'cost' : fields.float("Cost", help="Unit Cost for this product line", readonly=True),
        'currency' : fields.many2one('res.currency', string="Currency", help="Currency in which Unit cost is expressed", readonly=True),
    }
    
class stock_partial_move(osv.osv_memory):
    _name = "stock.partial.move"
    _description = "Partial Move"
    _columns = {
        'date': fields.datetime('Date', required=True),
        'type': fields.char("Type", size=3),
        'product_moves' : fields.one2many('stock.move.memory', 'wizard_id', 'Moves'),
     }
    
    def view_init(self, cr, uid, fields_list, context=None):
        res = super(stock_partial_move, self).view_init(cr, uid, fields_list, context=context)
        move_obj = self.pool.get('stock.move')
    
        if not context:
            context = {}
        for move in move_obj.browse(cr, uid, context.get('active_ids', [])):
            if move.state in ('done', 'cancel'):
                raise osv.except_osv(_('Invalid action !'), _('Cannot deliver products which are already delivered !'))
            
        return res
    
    
    def __create_partial_move_memory(self, move):
        move_memory = {
            'product_id' : move.product_id.id,
            'quantity' : move.product_qty,
            'product_uom' : move.product_uom.id,
            'prodlot_id' : move.prodlot_id.id,
            'move_id' : move.id,
        }
        if move.picking_id.type == 'in':
            move_memory.update({
                'cost' : move.product_id.standard_price,
                'currency' : move.product_id.company_id.currency_id.id,
            })
        return move_memory

    def __get_active_stock_moves(self, cr, uid, context=None):
        move_obj = self.pool.get('stock.move')
        if not context:
            context = {}
               
        res = []
        for move in move_obj.browse(cr, uid, context.get('active_ids', [])):
            if move.state in ('done', 'cancel'):
                continue           
            res.append(self.__create_partial_move_memory(move))
            
        return res
    
    _defaults = {
        'product_moves' : __get_active_stock_moves,
        'date' : time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        height = 2 * 25;
        message = {
                'title' : _('Deliver Products'),
                'info' : _('Delivery Information'),
                'button' : _('Deliver'),
                }
        if context:
            height = (len(context.get('active_ids', [])) + 1) * 25  
            if context.get('product_receive', False):
                message = {
                    'title' : _('Receive Products'),
                    'info' : _('Receive Information'),
                    'button' : _('Receive'),
                }
        message['height'] = height       
                
        
        result = super(stock_partial_move, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
        _moves_fields = result['fields']
        _moves_fields.update({'product_moves' : 
                            { 
                                'relation': 'stock.move.memory',
                                'type' : 'one2many',
                                'string' : 'Product Moves',
                            }
                            })
        
        _moves_arch_lst = """
                <form string="%(title)s">
                    <separator colspan="4" string="%(info)s"/>
                    <field name="date" colspan="2"/>
                    <separator colspan="4" string="Move Detail"/>
                    <field name="product_moves" colspan="4" nolabel="1" width="550" height="200" />
                    <separator string="" colspan="4" />
                    <label string="" colspan="2"/>
                    <group col="2" colspan="2">
                        <button icon='gtk-cancel' special="cancel" string="_Cancel" />
                        <button name="do_partial" string="%(button)s"
                            colspan="1" type="object" icon="gtk-apply" />
                    </group>
                </form> """ % message
        
        result['arch'] = _moves_arch_lst
        result['fields'] = _moves_fields
        return result
   
    def do_partial(self, cr, uid, ids, context):
        """ Makes partial moves and pickings done.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values
        @param context: A standard dictionary
        @return: A dictionary which of fields with values.
        """
    

        move_obj = self.pool.get('stock.move')
        
        move_ids = context.get('active_ids', False)
        partial = self.browse(cr, uid, ids[0], context)
        partial_datas = {
            'delivery_date' : partial.date
        }
        
        p_moves = {}
        for product_move in partial.product_moves:
            p_moves[product_move.move_id.id] = product_move
            
        moves_ids_final = []
        for move in move_obj.browse(cr, uid, move_ids):
            if move.state in ('done', 'cancel'):
                continue
            if not p_moves.get(move.id, False):
                continue
            partial_datas['move%s' % (move.id)] = {
                'product_id' : p_moves[move.id].product_id.id,
                'product_qty' : p_moves[move.id].quantity,
                'product_uom' : p_moves[move.id].product_uom.id,
                'prodlot_id' : p_moves[move.id].prodlot_id.id,
            }
            moves_ids_final.append(move.id)
            if (move.picking_id.type == 'in') and (move.product_id.cost_method == 'average'):
                partial_datas['move%s' % (move.id)].update({
                    'product_price' : p_moves[move.id].cost,
                    'product_currency': p_moves[move.id].currency.id,
                })
                
                
        move_obj.do_partial(cr, uid, moves_ids_final, partial_datas, context=context)
        return {}

stock_partial_move()
stock_partial_move_memory()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

