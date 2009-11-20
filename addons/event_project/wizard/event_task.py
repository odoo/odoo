# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
import pooler
from tools.translate import _

def _event_tasks(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname) 
    mod_obj = pool.get('ir.model.data') 
    result = mod_obj._get_id(cr, uid, 'project', 'view_task_search_form')
    id = mod_obj.read(cr, uid, result, ['res_id'])    
    event_id = data['id']
    cr.execute('SELECT project_id FROM event_event WHERE id = %s', (event_id, ))
    res = cr.fetchone()
    if not res[0]:
        raise wizard.except_wizard(_('Error !'), _('No project defined for this event.\nYou can create one with the retro-planning button !'))
    value = {
        'domain': [('project_id', '=', res[0])],
        'name': 'Tasks',
        'view_type': 'form',
        'view_mode': 'tree,form,calendar',
        'res_model': 'project.task',
        'context': { },
        'type': 'ir.actions.act_window',
        'search_view_id': id['res_id']         
    }
    return value

class wizard_event_tasks(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'action',
                'action': _event_tasks,
                'state': 'end'
            }
        },
    }
wizard_event_tasks("wizard_event_tasks")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

