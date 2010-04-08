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
from tools.translate import _
import netsvc
import pooler
import time

class stock_partial_move(osv.osv_memory):
    _name = "stock.partial.move"
    _description = "Partial Move"
    _columns = {
        'date': fields.datetime('Date', required=True),
    }

    def view_init(self, cr, uid, fields_list, context=None):
        res = super(stock_partial_move, self).view_init(cr, uid, fields_list, context=context)
        move_obj = self.pool.get('stock.move')
        if not context:
            context={}
        moveids = []
        for m in move_obj.browse(cr, uid, context.get('active_ids', [])):
            if m.state in ('done', 'cancel'):
                continue
            if 'move%s_product_id'%(m.id) not in self._columns:
                self._columns['move%s_product_id'%(m.id)] = fields.many2one('product.product',string="Product")
            if 'move%s_product_qty'%(m.id) not in self._columns:
                self._columns['move%s_product_qty'%(m.id)] = fields.float("Quantity")
            if 'move%s_product_uom'%(m.id) not in self._columns:
                self._columns['move%s_product_uom'%(m.id)] = fields.many2one('product.uom',string="Product UOM")

            if (m.picking_id.type == 'in') and (m.product_id.cost_method == 'average'):
                if 'move%s_product_price'%(m.id) not in self._columns:
                    self._columns['move%s_product_price'%(m.id)] = fields.float("Price")
                if 'move%s_product_currency'%(m.id) not in self._columns:
                    self._columns['move%s_product_currency'%(m.id)] = fields.many2one('res.currency',string="Currency")
        return res

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False,submenu=False):
        result = super(stock_partial_move, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar,submenu)
        move_obj = self.pool.get('stock.move')
        move_ids = context.get('active_ids', False)
        move_ids = move_obj.search(cr, uid, [('id','in',move_ids)])
        _moves_arch_lst = """<form string="Deliver Products">
                        <separator colspan="4" string="Information"/>
                    	<field name="date" colspan="4" />
                    	<newline/>
                        <separator colspan="4" string="Move Detail"/>
                    	"""
        _moves_fields = result['fields']
        if move_ids and view_type in ['form']:
            for m in move_obj.browse(cr, uid, move_ids, context):
                if m.state in ('done', 'cancel'):
                    continue
                _moves_fields.update({
                    'move%s_product_id'%(m.id)  : {
                                'string': _('Product'),
                                'type' : 'many2one',
                                'relation': 'product.product',
                                'required' : True,
                                'readonly' : True,
                                },
                    'move%s_product_qty'%(m.id) : {
                                'string': _('Quantity'),
                                'type' : 'float',
                                'required': True,
                                },
                    'move%s_product_uom'%(m.id) : {
                                'string': _('Product UOM'),
                                'type' : 'many2one',
                                'relation': 'product.uom',
                                'required' : True,
                                'readonly' : True,
                                }
                })

                _moves_arch_lst += """
                    <group colspan="4" col="10">
                    <field name="move%s_product_id" nolabel="1"/>
                    <field name="move%s_product_qty" string="Qty" />
                    <field name="move%s_product_uom" nolabel="1" />
                """%(m.id, m.id, m.id)
                if (m.picking_id.type == 'in') and (m.product_id.cost_method == 'average'):
                    _moves_fields.update({
                        'move%s_product_price'%(m.id) : {
                                'string': _('Price'),
                                'type' : 'float',
                                },
                        'move%s_product_currency'%(m.id): {
                                'string': _('Currency'),
                                'type' : 'float',
                                'type' : 'many2one',
                                'relation': 'res.currency',
                                }
                    })
                    _moves_arch_lst += """
                        <field name="move%s_product_price" />
                        <field name="move%s_product_currency" nolabel="1"/>
                    """%(m.id, m.id)
                _moves_arch_lst += """
                    </group>
                    """
        _moves_arch_lst += """
                <separator string="" colspan="4" />
                <label string="" colspan="2"/>
                <group col="2" colspan="2">
        		<button icon='gtk-cancel' special="cancel"
        			string="_Cancel" />
        		<button name="do_partial" string="_Deliver"
        			colspan="1" type="object" icon="gtk-apply" />
        	</group>                	
        </form>"""
        result['arch'] = _moves_arch_lst
        result['fields'] = _moves_fields
        return result

    def default_get(self, cr, uid, fields, context=None):
        """
             To get default values for the object.

             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param fields: List of fields for which we want default values
             @param context: A standard dictionary

             @return: A dictionary which of fields with values.

        """

        res = super(stock_partial_move, self).default_get(cr, uid, fields, context=context)
        move_obj = self.pool.get('stock.move')
        if not context:
            context={}
        moveids = []
        if 'date' in fields:
            res.update({'date': time.strftime('%Y-%m-%d %H:%M:%S')})
        for m in move_obj.browse(cr, uid, context.get('active_ids', [])):
            if m.state in ('done', 'cancel'):
                continue
            if 'move%s_product_id'%(m.id) in fields:
                res['move%s_product_id'%(m.id)] = m.product_id.id
            if 'move%s_product_qty'%(m.id) in fields:
                res['move%s_product_qty'%(m.id)] = m.product_qty
            if 'move%s_product_uom'%(m.id) in fields:
                res['move%s_product_uom'%(m.id)] = m.product_uom.id

            if (m.picking_id.type == 'in') and (m.product_id.cost_method == 'average'):
                price = 0
                if hasattr(m, 'purchase_line_id') and m.purchase_line_id:
                    price = m.purchase_line_id.price_unit

                currency = False
                if hasattr(m.picking_id, 'purchase_id') and m.picking_id.purchase_id:
                    currency = m.picking_id.purchase_id.pricelist_id.currency_id.id

                if 'move%s_product_price'%(m.id) in fields:
                    res['move%s_product_price'%(m.id)] = price
                if 'move%s_product_currency'%(m.id) in fields:
                    res['move%s_product_currency'%(m.id)] = currency
        return res

    def do_partial(self, cr, uid, ids, context):
        move_obj = self.pool.get('stock.move')
        move_ids = context.get('active_ids', False)
        partial = self.browse(cr, uid, ids[0], context)
        partial_datas = {
            'delivery_date' : partial.date
        }
        for m in move_obj.browse(cr, uid, move_ids):
            if m.state in ('done', 'cancel'):
                continue
            partial_datas['move%s'%(m.id)] = {
                'product_id' : getattr(partial, 'move%s_product_id'%(m.id)).id,
                'product_qty' : getattr(partial, 'move%s_product_qty'%(m.id)),
                'product_uom' : getattr(partial, 'move%s_product_uom'%(m.id)).id
            }

            if (m.picking_id.type == 'in') and (m.product_id.cost_method == 'average'):
                partial_datas['move%s'%(m.id)].update({
                    'product_price' : getattr(partial, 'move%s_product_price'%(m.id)),
                    'product_currency': getattr(partial, 'move%s_product_currency'%(m.id)).id
                })

        res = move_obj.do_partial(cr, uid, move_ids, partial_datas, context=context)
        return {}

stock_partial_move()

