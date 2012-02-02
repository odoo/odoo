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
import wizard
from osv import osv
from osv import fields
import pooler
from tools.translate import _

class create_graph(osv.osv_memory):
    _name = "create.relation.graph"

    def get_graph(self, cr, uid, datas, context=None):
        mod_obj = pooler.get_pool(cr.dbname).get('ir.module.module')
        modules = mod_obj.browse(cr, uid, context['active_ids'], context=context)
        for module in modules:
            module_data = mod_obj.get_relation_graph(cr, uid, module.name, context=context)
            if module_data['module_file']:
                mod_obj.write(cr, uid, [module.id], {'file_graph': module_data['module_file']}, context=context)
        return {'type': 'ir.actions.act_window_close'}

create_graph()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
