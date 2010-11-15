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

from osv import osv, fields

class stock_split_move_line(osv.osv_memory):
    _name = 'stock.move.line.split'
    _description = "Split Moves"
    
    def default_get(self, cr, uid, fields, context):
        """ To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values 
         @param context: A standard dictionary 
         @return: A dictionary which of fields with values. 
        """ 
        res = super(stock_split_move_line, self).default_get(cr, uid, fields, context=context)
        record_id = context and context.get('active_id', False) or False
        pick_obj = self.pool.get('stock.picking')
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        for m in [line for line in pick.move_lines]:
            res['move%s'%(m.id)] = m.product_qty
        return res
    
    def view_init(self, cr, uid, fields_list, context=None):
        """ Creates view dynamically and adding fields at runtime.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary 
         @return: New arch of view with new columns.
        """
        res = super(stock_split_move_line, self).view_init(cr, uid, fields_list, context=context)
        record_id = context and context.get('active_id', False) or False
        if record_id:
            pick_obj = self.pool.get('stock.picking')
            try:
                pick = pick_obj.browse(cr, uid, record_id, context=context)
                for m in [line for line in pick.move_lines]:
                    if 'move%s' % m.id not in self._columns:
                        self._columns['move%s' % m.id] = fields.float(string=m.product_id.name)
            except:
                return res
        return res
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', 
                        context=None, toolbar=False, submenu=False):
        """ Changes the view dynamically
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary 
         @return: New arch of view.
        """
        res = super(stock_split_move_line, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        record_id = context and context.get('active_id', False) or False
        assert record_id,'Active ID not found'
        pick_obj = self.pool.get('stock.picking')
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        arch_lst = ['<?xml version="1.0"?>', '<form string="Split lines">', '<label string="Indicate here the quantity of the new line. A quantity of zero will not split the line." colspan="4"/>']
        for m in [line for line in pick.move_lines]:
            quantity = m.product_qty
            arch_lst.append('<field name="move%s" />\n<newline />' % (m.id,))
            res['fields']['move%s' % m.id] = {'string' : m.product_id.name, 'type' : 'float', 'required' : True}
        arch_lst.append('<group col="2" colspan="4">')
        arch_lst.append('<button icon="gtk-cancel" special="cancel" string="Cancel" />')
        arch_lst.append('<button name="split_lines" string="Split" colspan="1" type="object" icon="gtk-apply" />')
        arch_lst.append('</group>')
        arch_lst.append('</form>')
        res['arch'] = '\n'.join(arch_lst)
        return res
    
    def split_lines(self, cr, uid, ids, context):
        """ Splits moves in quantity given in the wizard.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: List of ids selected 
         @param context: A standard dictionary 
         @return: A dictionary which of fields with values. 
        """ 
        move_obj = self.pool.get('stock.move')
        record_id = context and context.get('active_id', False) or False
        pick_obj = self.pool.get('stock.picking')
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        data = self.read(cr, uid, ids[0])
        for move in pick.move_lines:
            quantity = data['move%s' % move.id]
            if 0 < quantity < move.product_qty:
                new_qty = move.product_qty - quantity
                new_uos_qty = new_qty / move.product_qty * move.product_uos_qty
                new_obj = move_obj.copy(cr, uid, move.id, {'product_qty' : new_qty, 'product_uos_qty': new_uos_qty, 'state':move.state})
                uos_qty = quantity / move.product_qty * move.product_uos_qty
                move_obj.write(cr, uid, [move.id], {'product_qty' : quantity, 'product_uos_qty': uos_qty})
        return {}
    
stock_split_move_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

