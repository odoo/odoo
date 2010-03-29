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
import project.project_resource as proj

compute_form = """<?xml version="1.0" ?>
<form string="Compute Scheduling of Tasks">
    <field name="project_id" colspan="4"/>
</form>"""

success_msg = """<?xml version="1.0" ?>
<form string="Compute Scheduling of Tasks">
    <label string="Task Scheduling completed successfully."/>
</form>"""

compute_fields = {
    'project_id': {'string':'Project', 'type':'many2one', 'relation': 'project.project', 'required':'True'},
}

class wizard_compute_tasks(wizard.interface):

    def _compute_date(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        project_pool = pool.get('project.project')
        task_pool = pool.get('project.task')
        resource_pool = pool.get('resource.resource')
        user_pool = pool.get('res.users')
        project_id = data['form']['project_id']
        project = project_pool.browse(cr,uid,project_id)
        task_ids = task_pool.search(cr,uid,[('project_id','=',project_id),('state','in',['draft','open','pending'])])
        if task_ids:
            wktime_cal = []
            task_ids.sort()
            task_obj = task_pool.browse(cr,uid,task_ids)
            calendar_id = project.resource_calendar_id.id
            start_date = project.date_start
            if not project.date_start:
                start_date = datetime.datetime.now().strftime("%Y-%m-%d")
            date_start = datetime.datetime.strftime(datetime.datetime.strptime(start_date,"%Y-%m-%d"),"%Y-%m-%d %H:%M")

#    To create resources which are the Project Members
            resource_objs = []
            for resource in project.members:
                leaves = []
                resource_id = resource_pool.search(cr,uid,[('user_id','=',resource.id)])
                if resource_id:
                    resource_obj = resource_pool.browse(cr,uid,resource_id)[0]
                    leaves = proj.leaves_resource(cr,uid,calendar_id or False ,resource_id,resource_obj.calendar_id.id)
                    resource_objs.append(classobj(str(resource.name),(Resource,),{'__doc__':resource.name,'__name__':resource.name,'vacation':tuple(leaves),'efficiency':resource_obj.time_efficiency}))

            priority_dict = {'0':1000,'1':800,'2':500,'3':300,'4':100}

#     To create dynamic no of tasks with the resource specified
            def tasks_resource(j,eff,priorty = 500,obj=None):
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
                title = project.name
                start = date_start
                resource = reduce(operator.or_,resource_objs)
                minimum_time_unit = 1

#    If project has calendar
                if calendar_id:
                    working_days = proj.compute_working_calendar(cr,uid,calendar_id)
                    vacation = tuple(proj.leaves_resource(cr,uid,calendar_id))

#    Dynamic Creation of tasks
                i = 0
                for each_task in task_obj:
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
                if loop_no == 0:
                    project_pool.write(cr,uid,[project_id],{'date':e_date})
                else:
                    user_id = user_pool.search(cr,uid,[('name','=',t.booked_resource[0].__name__)])
                    task_pool.write(cr,uid,[task_obj[loop_no-1].id],{'date_start':s_date.strftime('%Y-%m-%d %H:%M:%S'),'date_deadline':e_date.strftime('%Y-%m-%d %H:%M:%S'),'user_id':user_id[0]})
                loop_no +=1
        return {}

    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':compute_form, 'fields':compute_fields, 'state':[
                ('end', 'Cancel', 'gtk-cancel'),
                ('compute', 'Compute', 'gtk-ok', True)
            ]},
        },


        'compute': {
            'actions': [_compute_date],
            'result': {'type':'form','arch':success_msg,'fields':{}, 'state':[('end', 'Ok', 'gtk-ok', True)]},
        }
    }
wizard_compute_tasks('wizard.compute.tasks')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
