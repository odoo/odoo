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

from osv import fields, osv
from caldav import calendar
from datetime import datetime
from tools.translate import _
from base_calendar import base_calendar
from project.project import task as base_project_task

class project_task(osv.osv):
    _name = "project.task"
    _inherit = ["project.task", "calendar.todo"]
    _columns = {
        # force inherit from project.project_task so that 
        # calendar.todo.active is masked oute
        'active': base_project_task._columns['active'],
        'date_deadline': base_project_task._columns['date_deadline'],
        'write_date': fields.datetime('Write Date'),
        'create_date': fields.datetime('Create Date', readonly=True),
        'attendee_ids': fields.many2many('calendar.attendee', \
                                         'task_attendee_rel', 'task_id', 'attendee_id', 'Attendees'),
        'state': fields.selection([('draft', 'Draft'),('open', 'In Progress'),('pending', 'Pending'), ('cancelled', 'Cancelled'), ('done', 'Done')], 'State', readonly=True, required=True,
                                  help='If the task is created the state is \'Draft\'.\n If the task is started, the state becomes \'In Progress\'.\n If review is needed the task is in \'Pending\' state.\
                                  \n If the task is over, the states is set to \'Done\'.'),
    }
    
    _defaults = {
        'state': 'draft',
    }

    def open_task(self, cr, uid, ids, context=None):
        """
        Open Task Form for Project Task.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of project task’s IDs
        @param context: A standard dictionary for contextual values
        @return: Dictionary value which open Project Task form.
        """

        data_pool = self.pool.get('ir.model.data')
        value = {}
        task_form_id = data_pool.get_object(cr, uid, 'project', 'view_task_form2')
        task_tree_id = data_pool.get_object(cr, uid, 'project', 'view_task_tree2')
        task_calendar_id = data_pool.get_object(cr, uid, 'project', 'view_task_calendar')
        for id in ids:
            value = {
                    'name': _('Tasks'),
                    'view_type': 'form',
                    'view_mode': 'form,tree',
                    'res_model': 'project.task',
                    'view_id': False,
                    'views': [(task_form_id, 'form'), (task_tree_id, 'tree'), (task_calendar_id, 'calendar')],
                    'type': 'ir.actions.act_window',
                    'res_id': base_calendar.base_calendar_id2real_id(id),
                    'nodestroy': True
                    }

        return value


    def import_cal(self, cr, uid, data, data_id=None, context=None):
        todo_obj = self.pool.get('basic.calendar.todo')
        vals = todo_obj.import_cal(cr, uid, data, context=context)
        return self.check_import(cr, uid, vals, context=context)

    def check_import(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        ids = []
        for val in vals:
            obj_tm = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.project_time_mode_id
            if not val.get('planned_hours', False):
                # 'Computes duration' in days
                plan = 0.0
                if val.get('date') and  val.get('date_deadline'):
                    start = datetime.strptime(val['date'], '%Y-%m-%d %H:%M:%S')
                    end = datetime.strptime(val['date_deadline'], '%Y-%m-%d %H:%M:%S')
                    diff = end - start
                    plan = (diff.seconds/float(86400) + diff.days) * obj_tm.factor
                val['planned_hours'] = plan
            else:
                # Converts timedelta into hours
                hours = (val['planned_hours'].seconds / float(3600)) + \
                                        (val['planned_hours'].days * 24)
                val['planned_hours'] = hours
            exists, r_id = calendar.uid2openobjectid(cr, val['id'], self._name, val.get('recurrent_id'))
            val.pop('id')
            if exists:
                self.write(cr, uid, [exists], val)
                ids.append(exists)
            else:
                #set user_id with id, needed later
                val.update({'user_id' : uid})
                task_id = self.create(cr, uid, val)
                ids.append(task_id)
        return ids

    def export_cal(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        task_datas = self.read(cr, uid, ids, [], context ={'read': True})
        tasks = []
        for task in task_datas:
            if task.get('planned_hours', None) and task.get('date_deadline', None):
                task.pop('planned_hours')
            tasks.append(task)
        todo_obj = self.pool.get('basic.calendar.todo')
        ical = todo_obj.export_cal(cr, uid, tasks, context={'model': self._name})
        calendar_val = ical.serialize()
        return calendar_val.replace('"', '').strip()

project_task()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
