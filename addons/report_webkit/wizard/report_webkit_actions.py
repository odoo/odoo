# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com) 
# All Right Reserved
#
# Author : Vincent Renaville
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
##############################################################################

from openerp.tools.translate import _
from openerp.osv import fields, osv
from openerp import pooler

class report_webkit_actions(osv.osv_memory):
    _name = "report.webkit.actions"
    _description = "Webkit Actions"
    _columns = {
       'print_button':fields.boolean('Add print button', help="Check this to add a Print action for this Report in the sidebar of the corresponding document types"),
       'open_action':fields.boolean('Open added action', help="Check this to view the newly added internal print action after creating it (technical view) "),
    }
    _defaults = {
             'print_button': lambda *a: True,
             'open_action': lambda *a: False,
    }    

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """ Changes the view dynamically
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary 
         @return: New arch of view.
        """
        if not context: context = {}
        res = super(report_webkit_actions, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        record_id = context and context.get('active_id', False) or False
        active_model = context.get('active_model')

        if not record_id or (active_model and active_model != 'ir.actions.report.xml'):
            return res
        
        report = self.pool.get('ir.actions.report.xml').browse(
                                                    cr, 
                                                    uid, 
                                                    context.get('active_id'), 
                                                    context=context
                                                )
        ir_values_obj = self.pool.get('ir.values')
        ids = ir_values_obj.search(
                            cr, 
                            uid, 
                            [('value','=',report.type+','+str(context.get('active_id')))]
                        )        

        if ids:
            res['arch'] = '''<form string="Add Print Buttons">
                                 <label string="Report Action already exist for this report."/>
                             </form> 
                            '''
        
        return res

    def do_action(self, cr, uid, ids, context=None):
        """ This Function Open added Action.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: List of report.webkit.actions's ID
         @param context: A standard dictionary 
         @return: Dictionary of ir.values form.
        """
        if context is None:
            context = {}        
        report_obj = self.pool.get('ir.actions.report.xml')
        for current in self.browse(cr, uid, ids, context=context):
            report = report_obj.browse(
                                                        cr, 
                                                        uid, 
                                                        context.get('active_id'), 
                                                        context=context
                                                    )
            if current.print_button:
                ir_values_obj = pooler.get_pool(cr.dbname).get('ir.values')
                res = ir_values_obj.set(
                                cr, 
                                uid, 
                                'action', 
                                'client_print_multi',
                                 report.report_name, 
                                 [report.model], 
                                 'ir.actions.report.xml,%d' % context.get('active_id', False), 
                                 isobject=True
                                )
            else:
                ir_values_obj = pooler.get_pool(cr.dbname).get('ir.values')
                res = ir_values_obj.set(
                                    cr, 
                                    uid, 
                                    'action', 
                                    'client_print_multi', 
                                    report.report_name, 
                                    [report.model,0], 
                                    'ir.actions.report.xml,%d' % context.get('active_id', False), 
                                    isobject=True
                                )
            if res[0]:
                if not current.open_action:
                    return {'type': 'ir.actions.act_window_close'}
                
                return {
                    'name': _('Client Actions Connections'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_id' : res[0],
                    'res_model': 'ir.values',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                }                   

report_webkit_actions()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
