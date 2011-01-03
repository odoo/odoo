
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

class stock_partial_picking(osv.osv_memory):
    _name = "stock.partial.picking"
    _description = "Partial Picking"
    _columns = {
        'date': fields.datetime('Date', required=True),
        'product_moves_out' : fields.one2many('stock.move.memory.out', 'wizard_id', 'Moves'),
        'product_moves_in' : fields.one2many('stock.move.memory.in', 'wizard_id', 'Moves'),
     }

    def __is_in(self,cr, uid, pick_ids):
        """
            @return: True if one of the moves has as picking type 'in'
        """
        if not pick_ids:
            return False

        pick_obj = self.pool.get('stock.picking')
        pick_ids = pick_obj.search(cr, uid, [('id','in',pick_ids)])


        for pick in pick_obj.browse(cr, uid, pick_ids):
            for move in pick.move_lines:
                if pick.type == 'in' and move.product_id.cost_method == 'average':
                    return True
        return False

    def __get_picking_type(self, cr, uid, pick_ids):
        if self.__is_in(cr, uid, pick_ids):
            return "product_moves_in"
        else:
            return "product_moves_out"

    def view_init(self, cr, uid, fields_list, context=None):
        res = super(stock_partial_picking, self).view_init(cr, uid, fields_list, context=context)
        return res

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False,submenu=False):
        result = super(stock_partial_picking, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar,submenu)


        picking_ids = context.get('active_ids', False)
        picking_type = self.__get_picking_type(cr, uid, picking_ids)

        _moves_arch_lst = """<form string="%s">
                        <field name="date" invisible="1"/>
                        <separator colspan="4" string="%s"/>
                        <field name="%s" colspan="4" nolabel="1" mode="tree,form" width="550" height="200" ></field>
                        """ % (_('Process Document'), _('Products'), picking_type)
        _moves_fields = result['fields']
        _moves_fields.update({
                            'product_moves_in' : {'relation': 'stock.move.memory.in', 'type' : 'one2many', 'string' : 'Product Moves'},
                            'product_moves_out' : {'relation': 'stock.move.memory.out', 'type' : 'one2many', 'string' : 'Product Moves'}
                            })

        _moves_arch_lst += """
                <separator string="" colspan="4" />
                <label string="" colspan="2"/>
                <group col="2" colspan="2">
                <button icon='gtk-cancel' special="cancel"
                    string="_Cancel" />
                <button name="do_partial" string="_Validate"
                    colspan="1" type="object" icon="gtk-go-forward" />
            </group>
        </form>"""
        result['arch'] = _moves_arch_lst
        result['fields'] = _moves_fields
        return result

    def __create_partial_picking_memory(self, picking, is_in):
        move_memory = {
            'product_id' : picking.product_id.id,
            'quantity' : picking.product_qty,
            'product_uom' : picking.product_uom.id,
            'prodlot_id' : picking.prodlot_id.id,
            'move_id' : picking.id,
        }

        if is_in:
            move_memory.update({
                'cost' : picking.price_unit,
                'currency' : picking.product_id.company_id.currency_id.id,
            })
        return move_memory

    def __get_active_stock_pickings(self, cr, uid, context=None):
        pick_obj = self.pool.get('stock.picking')
        if not context:
            context = {}

        res = []
        for pick in pick_obj.browse(cr, uid, context.get('active_ids', []), context):
            need_product_cost = (pick.type == 'in')
            for m in pick.move_lines:
                if m.state in ('done', 'cancel'):
                    continue
                res.append(self.__create_partial_picking_memory(m, need_product_cost))

        return res

    _defaults = {
        'product_moves_in' : __get_active_stock_pickings,
        'product_moves_out' : __get_active_stock_pickings,
        'date' : lambda *a : time.strftime('%Y-%m-%d %H:%M:%S'),
    }


    def do_partial(self, cr, uid, ids, context=None):
        """ Makes partial moves and pickings done.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values
        @param context: A standard dictionary
        @return: A dictionary which of fields with values.
        """
        pick_obj = self.pool.get('stock.picking')
        picking_ids = context.get('active_ids', False)
        partial = self.browse(cr, uid, ids[0], context=context)
        partial_datas = {
            'delivery_date' : partial.date
        }

        for pick in pick_obj.browse(cr, uid, picking_ids, context=context):
            need_product_cost = (pick.type == 'in')
            moves_list = need_product_cost and partial.product_moves_in  or partial.product_moves_out
            p_moves = {}
            for product_move in moves_list:
                p_moves[product_move.move_id.id] = product_move


            for move in pick.move_lines:
                if move.state in ('done', 'cancel'):
                    continue
                if not p_moves.get(move.id):
                    continue

                partial_datas['move%s' % (move.id)] = {
                    'product_id' : p_moves[move.id].id,
                    'product_qty' : p_moves[move.id].quantity,
                    'product_uom' :p_moves[move.id].product_uom.id,
                    'prodlot_id' : p_moves[move.id].prodlot_id.id,
                }


                if (move.picking_id.type == 'in') and (move.product_id.cost_method == 'average'):
                    partial_datas['move%s' % (move.id)].update({
                                                    'product_price' : p_moves[move.id].cost,
                                                    'product_currency': p_moves[move.id].currency.id,
                                                    })
        pick_obj.do_partial(cr, uid, picking_ids, partial_datas, context=context)
        return {}




stock_partial_picking()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

