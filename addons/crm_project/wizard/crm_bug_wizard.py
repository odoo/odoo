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

from mx.DateTime import now

import wizard
import netsvc
import ir
import pooler
from tools.translate import _

class bug2task(wizard.interface):

    def _check_state(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        case_obj = pool.get('crm.project.bug')
        for case in case_obj.browse(cr, uid, data['ids']):
            if case.state != 'open':
                raise wizard.except_wizard(_('Warning !'),
                    _('Bugs or Feature Requests should be in \'Open\' state before converting into Task.'))
        return {}

    def _makeTask(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        data_obj = pool.get('ir.model.data')
        result = data_obj._get_id(cr, uid, 'project', 'view_task_search_form')
        res = data_obj.read(cr, uid, result, ['res_id'])


        id2 = data_obj._get_id(cr, uid, 'project', 'view_task_form2')
        id3 = data_obj._get_id(cr, uid, 'project', 'view_task_tree2')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id

        bug_case_obj = pool.get('crm.project.bug')
        task_obj = pool.get('project.task')
        for bug in bug_case_obj.browse(cr, uid, data['ids']):
            new_task_id = task_obj.create(cr, uid, {
                'name': bug.name,
                'partner_id': bug.partner_id.id,
                'description':bug.description,
                'date': bug.date,
                'project_id':bug.project_id.id,
                'priority':bug.priority,
                'user_id':bug.user_id.id,
                'planned_hours': 0.0,
            })

            new_task = task_obj.browse(cr, uid, new_task_id)

            vals = {
                'task_id': new_task_id,
                }

            bug_case_obj.write(cr, uid, [bug.id], vals)

        value = {
            'name': _('Tasks'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'project.task',
            'res_id': int(new_task_id),
            'view_id': False,
            'views': [(id2, 'form'), (id3, 'tree'), (False, 'calendar'), (False, 'graph')],
            'type': 'ir.actions.act_window',
            'search_view_id': res['res_id']
        }
        return value

    states = {
        'init': {
            'actions': [_check_state],
            'result': {'type': 'action', 'action': _makeTask, 'state':'end' }
        }
    }

bug2task('crm.bug.task_set')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
