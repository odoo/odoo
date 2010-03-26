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

class stock_partial_picking(osv.osv_memory):
    _name = "stock.partial.picking"
    _description = "Partial Picking"
    _columns = {
                'date': fields.datetime('Date', required=True),
                'partner_id': fields.many2one('res.partner',string="Partner", required=True),
                'address_id': fields.many2one('res.partner.address', 'Delivery Address', help="Address where goods are to be delivered", required=True),
                               
     }

    def view_init(self, cr, uid, fields_list, context=None):
        res = super(stock_partial_picking, self).view_init(cr, uid, fields_list, context=context)
        pick_obj = self.pool.get('stock.picking')        
        if not context:
            context={}
        moveids = []
        for pick in pick_obj.browse(cr, uid, context.get('active_ids', [])):            
            for m in pick.move_lines:
                if m.state in ('done', 'cancel'):
                    continue
                if 'move%s_product_id'%(m.id) not in self._columns:
                    self._columns['move%s_product_id'%(m.id)] = fields.many2one('product.product',string="Product")
                if 'move%s_product_qty'%(m.id) not in self._columns:
                    self._columns['move%s_product_qty'%(m.id)] = fields.float("Quantity")
                if 'move%s_product_uom'%(m.id) not in self._columns:
                    self._columns['move%s_product_uom'%(m.id)] = fields.many2one('product.uom',string="Product UOM")

                if (pick.type == 'in') and (m.product_id.cost_method == 'average'):
                    if 'move%s_product_price'%(m.id) not in self._columns:
                        self._columns['move%s_product_price'%(m.id)] = fields.float("Price")
                    if 'move%s_product_currency'%(m.id) not in self._columns:
                        self._columns['move%s_product_currency'%(m.id)] = fields.many2one('res.currency',string="Currency")
        return res   

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False,submenu=False):
        result = super(stock_partial_picking, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar,submenu)        
        pick_obj = self.pool.get('stock.picking')
        picking_ids = context.get('active_ids', False)        
        if not picking_ids:
            return result
        if view_type in ['form']:
            _moves_arch_lst = """<form string="Deliver Products">
                        <separator colspan="4" string="Delivery Information"/>
                    	<field name="date" colspan="4" />
                    	<field name="partner_id"/>
                    	<field name="address_id"/>
                    	<newline/>
                        <separator colspan="4" string="Move Detail"/>
                    	"""
            _moves_fields = result['fields']
            for pick in pick_obj.browse(cr, uid, picking_ids, context):
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
                                    }
                    })                
                    
                    _moves_arch_lst += """
                        <group colspan="4" col="10">
                        <field name="move%s_product_id" nolabel="1"/>
                        <field name="move%s_product_qty" string="Qty" />
                        <field name="move%s_product_uom" nolabel="1" />
                    """%(m.id, m.id, m.id)
                    if (pick.type == 'in') and (m.product_id.cost_method == 'average'):                        
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

        res = super(stock_partial_picking, self).default_get(cr, uid, fields, context=context)
        pick_obj = self.pool.get('stock.picking')        
        if not context:
            context={}
        moveids = []
        for pick in pick_obj.browse(cr, uid, context.get('active_ids', [])):
            if 'partner_id' in fields:
                res.update({'partner_id': pick.address_id.partner_id.id})                
            if 'address_id' in fields:
                res.update({'address_id': pick.address_id.id})                        
            if 'date' in fields:
                res.update({'date': pick.date})
            for m in pick.move_lines:
                if m.state in ('done', 'cancel'):
                    continue
                if 'move%s_product_id'%(m.id) in fields:
                    res['move%s_product_id'%(m.id)] = m.product_id.id
                if 'move%s_product_qty'%(m.id) in fields:
                    res['move%s_product_qty'%(m.id)] = m.product_qty
                if 'move%s_product_uom'%(m.id) in fields:
                    res['move%s_product_uom'%(m.id)] = m.product_uom.id

                if (pick.type == 'in') and (m.product_id.cost_method == 'average'):
                    price = 0
                    if hasattr(m, 'purchase_line_id') and m.purchase_line_id:
                        price = m.purchase_line_id.price_unit

                    currency = False
                    if hasattr(pick, 'purchase_id') and pick.purchase_id:
                        currency = pick.purchase_id.pricelist_id.currency_id.id
        
                    if 'move%s_product_price'%(m.id) in fields:
                        res['move%s_product_price'%(m.id)] = price
                    if 'move%s_product_currency'%(m.id) in fields:
                        res['move%s_product_currency'%(m.id)] = currency
        return res   

    def do_partial(self, cr, uid, ids, context):    
        pick_obj = self.pool.get('stock.picking')    
        picking_ids = context.get('active_ids', False)
        partial = self.browse(cr, uid, ids[0], context)
        partial_datas = {
            'partner_id' : partial.partner_id and partial.partner_id.id or False,
            'address_id' : partial.address_id and partial.address_id.id or False,
            'delivery_date' : partial.date         
        }
        for pick in pick_obj.browse(cr, uid, picking_ids):
            for m in pick.move_lines:
                if m.state in ('done', 'cancel'):
                    continue
                partial_datas['move%s'%(m.id)] = {
                    'product_id' : getattr(partial, 'move%s_product_id'%(m.id)).id,
                    'product_qty' : getattr(partial, 'move%s_product_qty'%(m.id)),
                    'product_uom' : getattr(partial, 'move%s_product_uom'%(m.id)).id
                }

                if (pick.type == 'in') and (m.product_id.cost_method == 'average'):   
                    partial_datas['move%s'%(m.id)].update({             
                        'product_price' : getattr(partial, 'move%s_product_price'%(m.id)),
                        'product_currency': getattr(partial, 'move%s_product_currency'%(m.id)).id
                    })  
        
        res = pick_obj.do_partial(cr, uid, picking_ids, partial_datas, context=context)
        return {}
 
stock_partial_picking()    



#_moves_arch_end = '''<?xml version="1.0"?>
#<form string="Picking result">
#    <label string="The picking has been successfully made !" colspan="4"/>
#    <field name="back_order_notification" colspan="4" nolabel="1"/>
#</form>'''

#_moves_fields_end = {
#    'back_order_notification': {'string':'Back Order' ,'type':'text', 'readonly':True}
#                     }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

