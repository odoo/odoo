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

class report_menu_create(osv.osv_memory):
    """
    Create Menu
    """
    _name = "report.menu.create"
    _description = "Menu Create"
    _columns = {
              'menu_name':fields.char('Menu Name', size=64, required=True),
              'menu_parent_id':fields.many2one('ir.ui.menu', 'Parent Menu', required=True),
               }
    
    def report_menu_create(self, cr, uid, ids, context=None):
        """
        Create Menu.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Report Menu Create's IDs
        @return: Dictionary {}.
        """
        if not context:
            context = {}
        context_id = context and context.get('active_id', False) or False
        if context_id:
            board = self.pool.get('base_report_creator.report').browse(cr, uid, context_id)
            view = board.view_type1
            if board.view_type2:
                view += ',' + board.view_type2
            if board.view_type3:
                view += ',' + board.view_type3
            action_id = self.pool.get('ir.actions.act_window').create(cr, uid, {
                'name': board.name,
                'view_type':'form',
                'view_mode':view,
                'context': "{'report_id':%d}" % (board.id,),
                'res_model': 'base_report_creator.report'
                })
        obj_menu = self.pool.get('ir.ui.menu')
        #start Loop
        for data in self.read(cr, uid, ids):
            obj_menu.create(cr, uid, {
                'name': data.get('menu_name'),
                'parent_id': data.get('menu_parent_id'),
                'icon': 'STOCK_SELECT_COLOR',
                'action': 'ir.actions.act_window, ' + str(action_id)
                }, context=context)
            return {}
        #End Loop
report_menu_create()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

