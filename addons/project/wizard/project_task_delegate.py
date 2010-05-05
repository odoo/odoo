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

from tools.translate import _
from osv import fields, osv

class project_task_delegate(osv.osv_memory):
    _name = 'project.task.delegate'
    _description = 'Task Delegate'

    _columns = {
        'name': fields.char('Delegated Title', size=64, required=True, help="New title of the task delegated to the user"),
        'prefix': fields.char('Your Task Title', size=64, required=True, help="New title of your own task to validate the work done"),
        'user_id': fields.many2one('res.users', 'Assign To', required=True, help="User you want to delegate this task to"),
        'new_task_description': fields.text('New Task Description', help="Reinclude the description of the task in the task of the user"),
        'planned_hours': fields.float('Planned Hours',  help="Estimated time to close this task by the delegated user"),
        'planned_hours_me': fields.float('Hours to Validate', required=True, help="Estimated time for you to validate the work done by the user to whom you delegate this task"),
        'state': fields.selection([('pending','Pending'),
                                   ('done','Done'),
                                     ],'Validation State', required=True, help="New state of your own task. Pending will be reopened automatically when the delegated task is closed"),
            }

    def _get_name(self, cr, uid, context={}):
        if 'active_id' in context:
            task = self.pool.get('project.task').browse(cr, uid, context['active_id'])
            if task.name.startswith(_('CHECK: ')):
                newname = task.name.strip(_('CHECK: '))
            else:
                newname = task.name or ''
            return newname
        return ''

    def _get_plan_hour(self, cr, uid, context={}):
        if 'active_id' in context:
            task = self.pool.get('project.task').browse(cr, uid, context['active_id'])
            return task.remaining_hours
        return 0.0

    def _get_prefix(self, cr, uid, context={}):
        if 'active_id' in context:
            task = self.pool.get('project.task').browse(cr, uid, context['active_id'])
            if task.name.startswith(_('CHECK: ')):
                newname = task.name.strip(_('CHECK: '))
            else:
                newname = task.name or ''
            return _('CHECK: ')+ newname
        return ''

    def _get_new_desc(self, cr, uid, context={}):
        if 'active_id' in context:
            task = self.pool.get('project.task').browse(cr, uid, context['active_id'])
            return task.description
        return ''

    _defaults = {
       'name': _get_name,
       'planned_hours': _get_plan_hour,
       'planned_hours_me': 1.0,
       'prefix': _get_prefix,
       'new_task_description': _get_new_desc,
       'state': 'pending',
               }

    def validate(self, cr, uid, ids, context={}):
        task_obj = self.pool.get('project.task')
        delegate_data = self.read(cr, uid, ids, context=context)[0]
        task = task_obj.browse(cr, uid, context['active_id'], context=context)
        newname = delegate_data['prefix'] or ''
        new_task_id = task_obj.copy(cr, uid, task.id, {
            'name': delegate_data['name'],
            'user_id': delegate_data['user_id'],
            'planned_hours': delegate_data['planned_hours'],
            'remaining_hours': delegate_data['planned_hours'],
            'parent_ids': [(6, 0, [task.id])],
            'state': 'open',
            'description': delegate_data['new_task_description'] or '',
            'child_ids': [],
            'work_ids': []
        })
        task_obj.write(cr, uid, [task.id], {
            'remaining_hours': delegate_data['planned_hours_me'],
            'planned_hours': delegate_data['planned_hours_me'] + (task.effective_hours or 0.0),
            'name': newname,
        })
        if delegate_data['state'] == 'pending':
            task_obj.do_pending(cr, uid, [task.id])
        else:
            task_obj.do_close(cr, uid, [task.id])
        return {}

project_task_delegate()
