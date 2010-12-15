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
     }

    def view_init(self, cr, uid, fields_list, context=None):
        res = super(stock_partial_picking, self).view_init(cr, uid, fields_list, context=context)
        pick_obj = self.pool.get('stock.picking')
        if not context:
            context={}
        for pick in pick_obj.browse(cr, uid, context.get('active_ids', [])):
            need_product_cost = (pick.type == 'in')
            for m in pick.move_lines:
                if m.state in ('done', 'cancel'):
                    continue
                if 'move%s_product_id'%(m.id) not in self._columns:
                    self._columns['move%s_product_id'%(m.id)] = fields.many2one('product.product',string="Product")
                if 'move%s_product_qty'%(m.id) not in self._columns:
                    self._columns['move%s_product_qty'%(m.id)] = fields.float("Quantity")
                if 'move%s_product_uom'%(m.id) not in self._columns:
                    self._columns['move%s_product_uom'%(m.id)] = fields.many2one('product.uom',string="Product UOM")
                if 'move%s_prodlot_id'%(m.id) not in self._columns:
                    self._columns['move%s_prodlot_id'%(m.id)] = fields.many2one('stock.production.lot', string="Lot")

                if (need_product_cost and m.product_id.cost_method == 'average'):
                    if 'move%s_product_price'%(m.id) not in self._columns:
                        self._columns['move%s_product_price'%(m.id)] = fields.float("Cost", help="Unit Cost for this product line")
                    if 'move%s_product_currency'%(m.id) not in self._columns:
                        self._columns['move%s_product_currency'%(m.id)] = fields.many2one('res.currency', string="Currency", help="Currency in which Unit cost is expressed")
        return res

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False,submenu=False):
        result = super(stock_partial_picking, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar,submenu)
        pick_obj = self.pool.get('stock.picking')
        picking_ids = context.get('active_ids', False)
        _moves_arch_lst = """<form string="%s">
                        <field name="date" invisible="1"/>
                        <separator colspan="4" string="%s"/>
                        """ % (_('Process Document'), _('Products'))
        _moves_fields = result['fields']
        if picking_ids and view_type in ['form']:
            for pick in pick_obj.browse(cr, uid, picking_ids, context):
                need_product_cost = (pick.type == 'in')
                for m in pick.move_lines:
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
                        },
                        'move%s_prodlot_id'%(m.id): {
                            'string': _('Production Lot'),
                            'type': 'many2one',
                            'relation': 'stock.production.lot',
                        }
                    })

                    invisible = "1"
                    if pick.type=='in' and m.product_id.track_incoming:
                        invisible=""
                    if pick.type=='out' and m.product_id.track_outgoing:
                        invisible=""

                        
                    _moves_arch_lst += """
                        <group colspan="4" col="10">
                        <field name="move%s_product_id" nolabel="1"/>
                        <field name="move%s_product_qty"/>
                        <field name="move%s_product_uom" nolabel="1" />
                        <field name="move%s_prodlot_id" domain="[('product_id','=',move%s_product_id)]" invisible="%s" />
                    """%(m.id, m.id, m.id, m.id,m.id, invisible)

                    if (need_product_cost and m.product_id.cost_method == 'average'):
                        _moves_fields.update({
                            'move%s_product_price'%(m.id) : {
                                'string': _('Cost'),
                                'type' : 'float',
                                'help': _('Unit Cost for this product line'),
                            },
                            'move%s_product_currency'%(m.id): {
                                'string': _('Currency'),
                                'type' : 'many2one',
                                'relation': 'res.currency',
                                'help': _("Currency in which Unit Cost is expressed"),
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
                <button name="do_partial" string="_Validate"
                    colspan="1" type="object" icon="gtk-go-forward" />
            </group>
        </form>"""
        result['arch'] = _moves_arch_lst
        result['fields'] = _moves_fields
        return result

    def default_get(self, cr, uid, fields, context=None):
        """ To get default values for the object.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values
        @param context: A standard dictionary
        @return: A dictionary which of fields with values.
        """

        res = super(stock_partial_picking, self).default_get(cr, uid, fields, context=context)
        pick_obj = self.pool.get('stock.picking')
        if not context:
            context={}
        if 'date' in fields:
            res.update({'date': time.strftime('%Y-%m-%d %H:%M:%S')})
        for pick in pick_obj.browse(cr, uid, context.get('active_ids', [])):
            need_product_cost = (pick.type == 'in')
            for m in pick.move_lines:
                if m.state in ('done', 'cancel'):
                    continue
                if 'move%s_product_id'%(m.id) in fields:
                    res['move%s_product_id'%(m.id)] = m.product_id.id
                if 'move%s_product_qty'%(m.id) in fields:
                    res['move%s_product_qty'%(m.id)] = m.product_qty
                if 'move%s_product_uom'%(m.id) in fields:
                    res['move%s_product_uom'%(m.id)] = m.product_uom.id
                if 'move%s_prodlot_id'%(m.id) in fields:
                    res['move%s_prodlot_id'%(m.id)] = m.prodlot_id.id
                if (need_product_cost and m.product_id.cost_method == 'average'):
                    # Always use default product cost and currency from Product Form, 
                    # which belong to the Company owning the product
                    currency = m.product_id.company_id.currency_id.id
                    price = m.product_id.standard_price
                    if 'move%s_product_price'%(m.id) in fields:
                        res['move%s_product_price'%(m.id)] = price
                    if 'move%s_product_currency'%(m.id) in fields:
                        res['move%s_product_currency'%(m.id)] = currency
        return res

    def do_partial(self, cr, uid, ids, context):
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
        partial = self.browse(cr, uid, ids[0], context)
        partial_datas = {
            'delivery_date' : partial.date
        }
        for pick in pick_obj.browse(cr, uid, picking_ids):
            need_product_cost = (pick.type == 'in')
            for m in pick.move_lines:
                if m.state in ('done', 'cancel'):
                    continue
                partial_datas['move%s'%(m.id)] = {
                    'product_id' : getattr(partial, 'move%s_product_id'%(m.id)).id,
                    'product_qty' : getattr(partial, 'move%s_product_qty'%(m.id)),
                    'product_uom' : getattr(partial, 'move%s_product_uom'%(m.id)).id,
                    'prodlot_id' : getattr(partial, 'move%s_prodlot_id'%(m.id)).id
                }

                if (need_product_cost and m.product_id.cost_method == 'average'):
                    partial_datas['move%s'%(m.id)].update({
                        'product_price' : getattr(partial, 'move%s_product_price'%(m.id)),
                        'product_currency': getattr(partial, 'move%s_product_currency'%(m.id)).id
                    })
        pick_obj.do_partial(cr, uid, picking_ids, partial_datas, context=context)
        return {}

stock_partial_picking()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

