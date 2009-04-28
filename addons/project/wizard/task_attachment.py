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

import wizard
import pooler

'''View the attachments of the parent + children tasks'''

def _show_attachment(self, cr, uid, data, context):
    task_obj = pooler.get_pool(cr.dbname).get('project.task')
    task_browse_id = task_obj.browse(cr, uid, [data['id']], context)[0]
    attachment_list = [child_id.id for child_id in task_browse_id.child_ids]
    attachment_list.extend([task_browse_id.parent_id.id])
    value = {
        'domain': [('res_model','=',data['model']),('res_id','in',attachment_list)],
        'name': 'Attachments',
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'ir.attachment',
        'context': { },
        'type': 'ir.actions.act_window'
    }
    return value
class wizard_attachment(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type':'action', 'action':_show_attachment, 'state': 'end'},
        },
    }
wizard_attachment('project.task.attachment')
