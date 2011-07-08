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

from osv import osv
from tools.translate import _

class base_module_configuration(osv.osv_memory):

    _name = "base.module.configuration"

    def start(self, cr, uid, ids, context=None):
        todo_ids = self.pool.get('ir.actions.todo').search(cr, uid, ['|', '|', ('type','=','normal_recurring'), ('state', '=', 'open'), '&', ('state', '=', 'skip'), ('type', '=', 'special')])
        if not todo_ids:
            # When there is no wizard todo it will display message
            data_obj = self.pool.get('ir.model.data')
            result = data_obj._get_id(cr, uid, 'base', 'view_base_module_configuration_form')
            view_id = data_obj.browse(cr, uid, result).res_id
            value = {
                    'name': _('System Configuration done'), 
                    'view_type': 'form', 
                    'view_mode': 'form', 
                    'res_model': 'base.module.configuration', 
                    'view_id': [view_id], 
                    'type': 'ir.actions.act_window', 
                    'target': 'new'
                }
            return value
        # Run the config wizards
        config_pool = self.pool.get('res.config')
        return config_pool.start(cr, uid, ids, context=context)

base_module_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
