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

import os

import wizard
from tools.translate import _
import pooler
from osv import osv, fields

class quality_check(osv.osv_memory):
    _name = "quality.check"
    _description = "Quality Check"

    def _create_quality_check(self, cr, uid, ids, context=None):
        obj_quality = self.pool.get('module.quality.check')
        objs_ids = []
        module_id = context.get('active_id', False)
        module_data = self.pool.get('ir.module.module').browse(cr, uid, module_id)
        data = obj_quality.check_quality(cr, uid, module_data.name, module_data.state)
        obj = obj_quality.create(cr, uid, data, context)
        objs_ids.append(obj)
        return objs_ids

    def open_quality_check(self, cr, uid, ids, context):
        obj_ids = self._create_quality_check(cr, uid, ids, context)
        return {
            'domain': "[('id','in', ["+','.join(map(str,obj_ids))+"])]",
            'name': _('Quality Check'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'module.quality.check',
            'type': 'ir.actions.act_window'
            }
quality_check()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: