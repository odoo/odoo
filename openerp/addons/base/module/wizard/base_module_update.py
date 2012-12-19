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

from openerp.osv import osv, fields

class base_module_update(osv.osv_memory):
    """ Update Module """

    _name = "base.module.update"
    _description = "Update Module"

    _columns = {
        'update': fields.integer('Number of modules updated', readonly=True),
        'add': fields.integer('Number of modules added', readonly=True),
        'state':fields.selection([('init','init'),('done','done')], 'Status', readonly=True),
    }

    _defaults = {  
        'state': 'init',
    }

    def update_module(self, cr, uid, ids, context=None):
        module_obj = self.pool.get('ir.module.module')
        update, add = module_obj.update_list(cr, uid,)
        self.write(cr, uid, ids, {'update': update, 'add': add, 'state': 'done'}, context=context)
        return False

    def action_module_open(self, cr, uid, ids, context):
        res = {
            'domain': str([]),
            'name': 'Modules',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'ir.module.module',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
