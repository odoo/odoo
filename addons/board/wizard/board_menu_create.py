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

class board_menu_create(osv.osv_memory):
    """
    Create Menu
    """
    def view_init(self, cr, uid, fields, context=None):
        """
        This function checks for precondition before wizard executes
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values

        check dashboard view on menu name field.
        @return: False
        """
        data = context and context.get('active_id', False) or False
        if data:
            return False


    def board_menu_create(self, cr, uid, ids, context=None):
        """
        Create Menu.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Board Menu Create's IDs
        @return: Dictionary {}.
        """
        if context is None:
            context = {}

        context_id = context and context.get('active_id', False) or False
        if context_id:
            board = self.pool.get('board.board').browse(cr, uid, context_id, context=context)
            action_id = self.pool.get('ir.actions.act_window').create(cr, uid, {
                'name': board.name,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'board.board',
                'view_id': board.view_id.id,
                'help': _('''<div class="oe_empty_custom_dashboard">
                  <p>
                    <b>This dashboard is empty.</b>
                  </p><p>
                    To add the first report into this dashboard, go to any
                    menu, switch to list or graph view, and click <i>'Add to
                    Dashboard'</i> in the extended search options.
                  </p><p>
                    You can filter and group data before inserting into the
                    dashboard using the search options.
                  </p>
              </div>
                ''')
                })
        obj_menu = self.pool.get('ir.ui.menu')
        #start Loop
        for data in self.browse(cr, uid, ids, context=context):
            obj_menu.create(cr, uid, {
                'name': data.menu_name,
                'parent_id': data.menu_parent_id.id,
                'action': 'ir.actions.act_window,' + str(action_id)
                }, context=context)
        #End Loop
        return {'type': 'ir.actions.act_window_close'}

    _name = "board.menu.create"
    _description = "Menu Create"

    _columns = {
             'menu_name': fields.char('Menu Name', size=64, required=True),
             'menu_parent_id': fields.many2one('ir.ui.menu', 'Parent Menu', required=True),
          }

board_menu_create()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

