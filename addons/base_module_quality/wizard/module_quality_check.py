# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import os

import wizard
import pooler
from osv import osv, fields

class quality_check(wizard.interface):

    def _create_quality_check(self, cr, uid, data, context={}):
        pool = pooler.get_pool(cr.dbname)
        obj_quality = pool.get('module.quality.check')
        objs = []
        for id in data['ids']:
            module_data = pool.get('ir.module.module').browse(cr, uid, id)
            data = obj_quality.check_quality(cr, uid, module_data.name, module_data.state)
            obj = obj_quality.create(cr, uid, data, context)
            objs.append(obj)
        return objs

    def _open_quality_check(self, cr, uid, data, context):
        obj_ids = self._create_quality_check(cr, uid, data, context)
        return {
            'domain': "[('id','in', ["+','.join(map(str,obj_ids))+"])]",
            'name': _('Quality Check'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'module.quality.check',
            'type': 'ir.actions.act_window'
            }

    states = {
        'init' : {
            'actions' : [],
            'result': {'type':'action', 'action':_open_quality_check, 'state':'end'}
        }
    }

quality_check("create_quality_check_wiz")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: