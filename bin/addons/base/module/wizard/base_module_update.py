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
import pooler
from osv import osv, fields

class base_module_update(osv.osv_memory):
    """ Update Module """

    _name = "base.module.update"
    _description = "Update Module"

    def update_module(self, cr, uid, ids, context):
        """
           Update Module

            @param cr: the current row, from the database cursor.
            @param uid: the current user’s ID for security checks.
            @param ids: the ID or list of IDs
            @param context: A standard dictionary
        """
        data_obj = self.pool.get('ir.model.data')
        id2 = data_obj._get_id(cr, uid, 'base', 'view_base_module_update_open')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'base.module.update.open',
            'views': [(id2, 'form')],
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',

        }

base_module_update()

class base_module_update_open(osv.osv_memory):
    """ Update Module Open """

    _name = "base.module.update.open"
    _description = "Update Module Open"

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values
        @return : default values of fields.
        """

        module_obj = self.pool.get('ir.module.module')
        update, add = module_obj.update_list(cr, uid,)
        return {'update': update, 'add': add}

    _columns = {
          'update': fields.integer('Number of modules updated', readonly=True),
          'add': fields.integer('Number of modules added', readonly=True),
    }

    def action_module_open(self, cr, uid, ids, context):
        """
           Update Module List Open

            @param cr: the current row, from the database cursor.
            @param uid: the current user’s ID for security checks.
            @param ids: the ID or list of IDs
            @param context: A standard dictionary
        """
        res = {
            'domain': str([]),
            'name': 'Module List',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'ir.module.module',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
        view_obj = self.pool.get('ir.ui.view')
        search_view_id = view_obj.search(cr, uid, [('name','=','ir.module.module.list.select')], context=context)
        if search_view_id:
            res.update({'search_view_id' : search_view_id[0]})
        return res

base_module_update_open()