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
import datetime
from resource.faces import *
from new import classobj
import operator
import time
import project.project_resource as proj

success_msg = """<?xml version="1.0" ?>
<form string="Compute Scheduling of Tasks">
    <label string="Task Scheduling completed successfully."/>
</form>"""

def resource_list(cr,uid,phase):
#    To create resources which are the Project Members

        resource_objs = []
        for resource in phase.resource_ids:
            res = resource.resource_id
            leaves = []
            resource_eff = res.time_efficiency
            resource_cal = res.calendar_id.id
            wktime_cal = proj.compute_working_calendar(cr,uid,resource_cal)
            leaves = proj.leaves_resource(cr,uid,phase.project_id.resource_calendar_id.id or False ,res.id,resource_cal)
            resource_objs.append(classobj(str(res.user_id.name),(Resource,),{'__doc__':res.user_id.name,'__name__':res.user_id.name,'vacation':tuple(leaves),'efficiency':resource_eff}))
        return resource_objs

class wizard_schedule_task(wizard.interface):

    def _compute_date(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        phase_pool = pool.get('project.phase')
        task_pool = pool.get('project.task')
        user_pool = pool.get('res.users')
        phase = phase_pool.browse(cr,uid,data['id'])
        task_ids = map(lambda x:x.id,(filter(lambda x:x.state in ['open','draft','pending'] ,phase.task_ids)))

        if task_ids:
            task_ids.sort()
            tasks = task_pool.browse(cr,uid,task_ids)
            wktime_cal = []
            start_date = str(phase.date_start)[:-9]
            if not phase.date_start:
                if not phase.project_id.date_start:
                    start_date = datetime.datetime.now().strftime("%Y-%m-%d")
                else:
                    start_date = phase.project_id.date_start
            date_start = datetime.datetime.strftime(datetime.datetime.strptime(start_date,"%Y-%m-%d"),"%Y-%m-%d %H:%M")
            calendar_id = phase.project_id.resource_calendar_id.id
            resource_objs = resource_list(cr,uid,phase)
            priority_dict = {'0':1000,'1':800,'2':500,'3':300,'4':100}

#     To create dynamic no of tasks with the resource specified
            def tasks_resource(j,eff,priorty = 500,obj=False):
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

#    Creating the project with all the tasks and resources
            def Project():
                title = "Test Project"
                start = date_start
                resource = reduce(operator.or_,resource_objs)
                minimum_time_unit = 1

#    If project has calendar
                if calendar_id:
                    working_days = proj.compute_working_calendar(cr,uid,calendar_id)
                    vacation = tuple(proj.leaves_resource(cr,uid,calendar_id))

#    Dynamic Creation of tasks
                i = 0
                for each_task in tasks:
                    hours = str(each_task.planned_hours / each_task.occupation_rate)+ 'H'
                    if each_task.priority in priority_dict.keys():
                        priorty = priority_dict[each_task.priority]
                    if each_task.user_id:
                       for resource_object in resource_objs:
                            if resource_object.__name__ == each_task.user_id.name:
                               task = tasks_resource(i,hours,priorty,resource_object)
                    else:
                        task = tasks_resource(i,hours,priorty)
                    i += 1

#    Writing back the dates
            project = BalancedProject(Project)
            loop_no = 0
            for t in project:
                s_date = t.start.to_datetime()
                e_date = t.end.to_datetime()
                if loop_no > 0:
                    user_id = user_pool.search(cr,uid,[('name','=',t.booked_resource[0].__name__)])
                    task_pool.write(cr,uid,[tasks[loop_no-1].id],{'date_start':s_date.strftime('%Y-%m-%d %H:%M:%S'),'date_deadline':e_date.strftime('%Y-%m-%d %H:%M:%S'),'user_id':user_id[0]},context={'scheduler':True})
                loop_no +=1
        return {}

    states = {
        'init': {
            'actions': [_compute_date],
            'result': {'type':'form','arch':success_msg,'fields':{}, 'state':[('end', 'Ok')]},
        }
    }
wizard_schedule_task('phase.schedule.tasks')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
