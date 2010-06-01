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
import datetime
from resource.faces import *
from new import classobj
import operator

from tools.translate import _
from osv import osv, fields

import working_calendar as wkcal

class project_schedule_task(osv.osv_memory):

    _name = "project.schedule.tasks"
    _description = 'project.schedule.tasks'
    _columns = {
        'msg': fields.char('Message', size=64)
                }
    _defaults = {
         'msg': 'Task Scheduling Completed Successfully'
                }

    def default_get(self, cr, uid, fields_list, context=None):
        res = super(project_schedule_task, self).default_get(cr, uid, fields_list, context)
        self.compute_date(cr, uid, context=context)
        return res

    def create_resources(self, cr, uid, phase, context=None):
        """
        Return a list of  Resource Class objects for the resources allocated to the phase.
        """
        resource_objs = []

        if context is None:
            context = {}

        for resource in phase.resource_ids:
            res = resource.resource_id
            leaves = []
            resource_eff = res.time_efficiency
            resource_cal = res.calendar_id.id
            if resource_cal:
                cal_id  = phase.project_id.resource_calendar_id and phase.project_id.resource_calendar_id.id or False
                leaves = wkcal.compute_leaves(cr, uid, cal_id, res.id, resource_cal, context=context)
            resource_objs.append(classobj(res.user_id.name.encode('utf8'), (Resource,),
                                         {'__doc__': res.user_id.name,
                                          '__name__': res.user_id.name,
                                          'vacation': tuple(leaves),
                                          'efficiency': resource_eff,
                                          }))
        return resource_objs

    def compute_date(self, cr, uid, context=None):
        """
        Schedule the tasks according to resource available and priority.
        """

        phase_obj = self.pool.get('project.phase')
        task_obj = self.pool.get('project.task')
        user_obj = self.pool.get('res.users')

        if context is None:
            context = {}

        if not 'active_id' in context:
            return {}
        phase = phase_obj.browse(cr, uid, context['active_id'], context=context)
        task_ids = map(lambda x : x.id, (filter(lambda x : x.state in ['open', 'draft', 'pending'] , phase.task_ids)))
        if task_ids:
            task_ids.sort()
            tasks = task_obj.browse(cr, uid, task_ids, context=context)
            start_date = str(phase.date_start)[:-9]
            if not phase.date_start:
                if not phase.project_id.date_start:
                    start_date = datetime.datetime.now().strftime("%Y-%m-%d")
                else:
                    start_date = phase.project_id.date_start
            date_start = datetime.datetime.strftime(datetime.datetime.strptime(start_date, "%Y-%m-%d"), "%Y-%m-%d %H:%M")
            calendar_id = phase.project_id.resource_calendar_id.id
            resources = self.create_resources(cr, uid, phase)
            priority_dict = {'0': 1000, '1': 800, '2': 500, '3': 300, '4': 100}
            # Create dynamic no of tasks with the resource specified
            def create_tasks(j, eff, priorty=500, obj=False):
                def task():
                    """
                    task is a dynamic method!
                    """
                    effort = eff
                    if obj:
                        resource = obj
                    priority = priorty
                task.__doc__ = "TaskNO%d" %j
                task.__name__ = "task%d" %j
                return task

            # Create a 'Faces' project with all the tasks and resources
            def Project():
                title = "Project"
                start = date_start
                try:
                    resource = reduce(operator.or_, resources)
                except:
                    raise osv.except_osv(_('Error'), _('Phase must have resources assigned !'))
                minimum_time_unit = 1
                if calendar_id:            # If project has working calendar
                    working_days = wkcal.compute_working_calendar(cr, uid, calendar_id)
                    vacation = tuple(wkcal.compute_leaves(cr, uid, calendar_id))
                # Dynamic creation of tasks
                i = 0
                for each_task in tasks:
                    hours = str(each_task.planned_hours / each_task.occupation_rate)+ 'H'
                    if each_task.priority in priority_dict.keys():
                        priorty = priority_dict[each_task.priority]
                    if each_task.user_id:
                       for resource in resources:
                            if resource.__name__ == each_task.user_id.name:
                               task = create_tasks(i, hours, priorty, resource)
                    else:
                        task = create_tasks(i, hours, priorty)
                    i += 1

            project = BalancedProject(Project)
            loop_no = 0
            # Write back the computed dates
            for t in project:
                s_date = t.start.to_datetime()
                e_date = t.end.to_datetime()
                if loop_no > 0:
                    ctx = context.copy()
                    ctx.update({'scheduler': True})
                    user_id = user_obj.search(cr, uid, [('name', '=', t.booked_resource[0].__name__)])
                    task_obj.write(cr, uid, [tasks[loop_no-1].id], {'date_start': s_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                                    'date_end': e_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                                    'user_id': user_id[0]},
                                                                    context=ctx)
                loop_no +=1
        return {}

project_schedule_task()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
