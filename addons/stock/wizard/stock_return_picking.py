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

import netsvc
import time

from osv import osv,fields
from tools.translate import _

class stock_return_picking(osv.osv_memory):
    _name = 'stock.return.picking'
    _description = 'Return Picking'

    def default_get(self, cr, uid, fields, context):
        """
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary with default values for all field in ``fields``
        """
        res = super(stock_return_picking, self).default_get(cr, uid, fields, context=context)
        record_id = context and context.get('active_id', False) or False
        pick_obj = self.pool.get('stock.picking')
        pick = pick_obj.browse(cr, uid, record_id)
        if pick:
            if 'invoice_state' in fields:
                if pick.invoice_state=='invoiced':
                    res['invoice_state'] = '2binvoiced'
                else:
                    res['invoice_state'] = 'none'
            for line in pick.move_lines:
                return_id = 'return%s'%(line.id)
                if return_id in fields:
                    res[return_id] = line.product_qty
        return res

    def view_init(self, cr, uid, fields_list, context=None):
        """ 
         Creates view dynamically and adding fields at runtime.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary 
         @return: New arch of view with new columns.
        """
        res = super(stock_return_picking, self).view_init(cr, uid, fields_list, context=context)
        record_id = context and context.get('active_id', False) 
        if record_id:
            pick_obj = self.pool.get('stock.picking')
            pick = pick_obj.browse(cr, uid, record_id)
            for m in [line for line in pick.move_lines]:
                if 'return%s'%(m.id) not in self._columns:
                    self._columns['return%s'%(m.id)] = fields.float(string=m.name, required=True)
                if 'invoice_state' not in self._columns:
                    self._columns['invoice_state'] = fields.selection([('2binvoiced', 'To be Invoiced'), ('none', 'None')], string='Invoice State', required=True)
                for rec in m.move_history_ids2:
                    if rec.product_qty==m.product_qty:
                        raise osv.except_osv(_('Warning !'), _("There is no product to return!"))
        return res
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', 
                        context=None, toolbar=False, submenu=False):
        """ 
         Changes the view dynamically
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary 
         @return: New arch of view.
        """
        res = super(stock_return_picking, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        record_id = context and context.get('active_id', False)
        active_model = context.get('active_model')
        if  active_model != 'stock.picking':
            return res
        if record_id:
            pick_obj = self.pool.get('stock.picking')
            pick = pick_obj.browse(cr, uid, record_id)
            if pick.state != 'done':
                raise osv.except_osv(_('Warning !'), _("The Picking is not completed yet!\nYou cannot return picking which is not in 'Done' state!"))
        
            return_history = {}
            for m_line in pick.move_lines:
                return_history[m_line.id] = 0
                for rec in m_line.move_history_ids2:
                    return_history[m_line.id] += rec.product_qty
            res['fields'].clear()
            arch_lst=['<?xml version="1.0"?>', '<form string="%s">' % _('Return lines'), '<label string="%s" colspan="4"/>' % _('Provide the quantities of the returned products.')]
            for m in [line for line in pick.move_lines]:
                quantity = m.product_qty
                if quantity > return_history[m.id] and (quantity - return_history[m.id])>0:
                    arch_lst.append('<field name="return%s"/>\n<newline/>' % (m.id,))
                    res['fields']['return%s' % m.id]={'string':m.name, 'type':'float', 'required':True} 
                    res.setdefault('returns', []).append(m.id)
#            if not res.get('returns',False): Todo : It may be used 
#                raise osv.except_osv(_('Warning!'),_('There is no product to return!'))
        
            arch_lst.append('<field name="invoice_state"/>\n<newline/>')
            res['fields']['invoice_state']={'string':_('Invoice state'), 'type':'selection','required':True, 'selection':[('2binvoiced', _('To Be Invoiced')), ('none', _('None'))]}
            arch_lst.append('<group col="2" colspan="4">')
            arch_lst.append('<button icon="gtk-cancel" special="cancel" string="Cancel" />')
            arch_lst.append('<button name="create_returns" string="Return" colspan="1" type="object" icon="gtk-apply" />')
            arch_lst.append('</group>')
            arch_lst.append('</form>')
            res['arch'] = '\n'.join(arch_lst)
        return res

    def create_returns(self, cr, uid, ids, context):
        """ 
         Creates return picking.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: List of ids selected 
         @param context: A standard dictionary 
         @return: A dictionary which of fields with values. 
        """ 
        record_id = context and context.get('active_id', False) or False
        move_obj = self.pool.get('stock.move')
        pick_obj = self.pool.get('stock.picking')
        uom_obj = self.pool.get('product.uom')
        wf_service = netsvc.LocalService("workflow")
    
        pick = pick_obj.browse(cr, uid, record_id)
        data = self.read(cr, uid, ids[0])
        new_picking = None
        date_cur = time.strftime('%Y-%m-%d %H:%M:%S')
    
        move_ids = [m.id for m in [line for line in pick.move_lines]]
        set_invoice_state_to_none = True
        for move in move_obj.browse(cr, uid, move_ids):
            if not new_picking:
                if pick.type=='out':
                    new_type = 'in'
                elif pick.type=='in':
                    new_type = 'out'
                else:
                    new_type = 'internal'
                new_picking = pick_obj.copy(cr, uid, pick.id, {'name':'%s (return)' % pick.name,
                        'move_lines':[], 'state':'draft', 'type':new_type,
                        'date':date_cur, 'invoice_state':data['invoice_state'],})
            new_location=move.location_dest_id.id
    
            new_qty = data['return%s' % move.id]
            returned_qty = move.product_qty
    
            for rec in move.move_history_ids2:
                returned_qty -= rec.product_qty
    
            if returned_qty != new_qty:
                set_invoice_state_to_none = False
    
            new_move=move_obj.copy(cr, uid, move.id, {
                'product_qty': new_qty,
                'product_uos_qty': uom_obj._compute_qty(cr, uid, move.product_uom.id,
                    new_qty, move.product_uos.id),
                'picking_id':new_picking, 'state':'draft',
                'location_id':new_location, 'location_dest_id':move.location_id.id,
                'date':date_cur, 'date_planned':date_cur,})
            move_obj.write(cr, uid, [move.id], {'move_history_ids2':[(4,new_move)]})
    
        if set_invoice_state_to_none:
            pick_obj.write(cr, uid, [pick.id], {'invoice_state':'none'})
        if new_picking:
            if new_picking:
                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_confirm', cr)
            pick_obj.force_assign(cr, uid, [new_picking], context)
            return {
                'domain': "[('id', 'in', ["+str(new_picking)+"])]",
                'name': 'Picking List',
                'view_type':'form',
                'view_mode':'tree,form',
                'res_model':'stock.picking',
                'view_id':False,
                'type':'ir.actions.act_window',
                'context':context,
            }            
        return {}
    
stock_return_picking()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

