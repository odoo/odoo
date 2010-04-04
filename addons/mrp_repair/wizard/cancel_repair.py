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
from osv import osv,fields
from tools.translate import _

class repair_cancel(osv.osv_memory):
    _name = 'mrp.repair.cancel'
    _description = 'Cancel Repair'

    def cancel_repair(self, cr, uid, ids, context):
        """ 
             Cancels the repair
        
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: List of IDs selected 
             @param context: A standard dictionary 
             
             @return:  
        
        """
        record_id = context and context.get('active_id', False) or False
        assert record_id, _('Active ID is not Found')
        repair_order_obj = self.pool.get('mrp.repair')
        repair_line_obj = self.pool.get('mrp.repair.line')
        repair_order = repair_order_obj.browse(cr, uid, record_id)
        
        if repair_order.invoiced or repair_order.invoice_method == 'none':
            repair_order_obj.action_cancel(cr, uid, [record_id], context=context)            
        else:
            raise osv.except_osv(_('Warning!'),_('Repair is not cancelled. It is not invoiced.'))
        
        return {}
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """ 
             Changes the view dynamically
        
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary 
             
             @return: New arch of view.
        
        """
        record_id = context and context.get('active_id', False) or False        
        res = super(repair_cancel, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        if record_id:
            try:
                repair_order = self.pool.get('mrp.repair').browse(cr, uid, record_id)
                if not repair_order.invoiced:
                    res['arch'] = """ <form string="Cancel Repair" colspan="4">
                                    <group col="2" colspan="2">
                                        <label string="Do you want to continue?" colspan="4"/>
                                        <separator colspan="4"/>
                                        <button icon="gtk-cancel" special="cancel" string="No" readonly="0"/>
                                        <button name="cancel_repair" string="Yes" type="object" icon="gtk-ok"/>
                                    </group>
                                </form>                             
                            """
            except:
                return res
        return res

repair_cancel()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

