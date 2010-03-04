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
    
    _columns = {
        'repair_id': fields.many2one('mrp.repair', 'Repair ID', readonly=True),
    }
    
    def cancel_repair(self, cr, uid, ids, context):
        cancel = self.browse(cr, uid, ids[0])
        repair_obj = self.pool.get('mrp.repair').browse(cr, uid, [cancel.repair_id.id])
        
        if repair_obj[0].invoiced or repair_obj[0].invoice_method == 'none':
            self.pool.get('mrp.repair').write(cr, uid, cancel.repair_id.id, {'state':'cancel'})
            mrp_line_obj = self.pool.get('mrp.repair.line')
            for line in repair_obj:
                mrp_line_obj.write(cr, uid, [l.id for l in line.operations], {'state': 'cancel'})
        else:
            raise osv.except_osv(_('Warning!'),_('Repair is not cancelled. It is not invoiced.'))
        return {}
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        record_id = context and context.get('record_id', False) or False
        res = super(repair_cancel, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        if record_id:
            repair_obj = self.pool.get('mrp.repair').browse(cr, uid, [record_id])[0]
            if not repair_obj.invoice_id:
                res['arch'] = """ <form string="Cancel Repair" colspan="4">
                                <field name="repair_id" invisible="1"/>
                                <newline/>
                                <group col="2" colspan="2">
                                    <button icon="gtk-cancel" special="cancel" string="No" readonly="0"/>
                                    <button name="cancel_repair" string="Yes" type="object" icon="gtk-ok"/>
                                </group>
                            </form>                             
                        """
        return res
    
    def default_get(self, cr, uid, fields, context=None):
        record_id = context and context.get('record_id', False) or False
        res = super(repair_cancel, self).default_get(cr, uid, fields, context=context)
        if record_id:
            repair_id = self.pool.get('mrp.repair').browse(cr, uid, record_id, context=context)
            res['repair_id'] = repair_id.id
        return res
   
repair_cancel()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

