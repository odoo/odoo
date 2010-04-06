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

class report_open(osv.osv_memory):
    """
    Open report
    """
    _name = "report.open"
    _description = __doc__

    def open_report(self, cr, uid, ids, context=None):
        """
        This Function opens base creator report  view
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of report open's IDs
        @param context: A standard dictionary for contextual values
        @return : Dictionary value for base creator report form
        """

        if not context:
            context = {}
            
        context_id = context and context.get('active_id', False) or False
        
        if context.get('report_id', False):
            raise  osv.except_osv(_('UserError'), _('No Wizards available for this object!'))
        
        rep = self.pool.get('base_report_creator.report').browse(cr, uid, context_id, context)
        view_mode = rep.view_type1
        
        if rep.view_type2:
            view_mode += ',' + rep.view_type2
        if rep.view_type3:
            view_mode += ',' + rep.view_type3
        value = {
            'name': rep.name, 
            'view_type': 'form', 
            'view_mode': view_mode, 
            'res_model': 'base_report_creator.report', 
            'context': {'report_id': context_id}, 
            'view_id': False, 
            'type': 'ir.actions.act_window'
        }
        
        return value

report_open()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
