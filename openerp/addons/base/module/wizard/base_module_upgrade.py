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
from tools.translate import _

class base_module_upgrade(osv.osv_memory):
    """ Module Upgrade """

    _name = "base.module.upgrade"
    _description = "Module Upgrade"

    _columns = {
        'module_info': fields.text('Modules to update',readonly=True),
    }


    def default_get(self, cr, uid, fields, context=None):
        """
        This function checks for precondition before wizard executes
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values
        """
        mod_obj = self.pool.get('ir.module.module')
        ids = context.get('modules', [])
        mode = context.get('mode', 'install')
        mode_string = {
                'install': 'Installed',
                'upgrade': 'Upgraded',
                'uninstall': 'Uninstalled'
            }
        res = mod_obj.read(cr, uid, ids, ['name'], context)
        return {'module_info': '\n'.join(map(lambda x: x['name']+' : '+ mode_string[mode], res))}


    def config(self, cr, uid, ids, context=None):
        return self.pool.get('res.config').next(cr, uid, [], context=context)

base_module_upgrade()
