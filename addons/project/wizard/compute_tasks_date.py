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

compute_form = """<?xml version="1.0" ?>
<form string="Compute Scheduling of Tasks">
    <field name="project_id" colspan="4"/>
    <field name= "date_from" colspan="4"/>
</form>"""

success_msg = """<?xml version="1.0" ?>
<form string="Compute Scheduling of Tasks">
    <label string="Task Scheduling completed successfully."/>
</form>"""

compute_fields = {
    'project_id': {'string':'Project', 'type':'many2one', 'relation': 'project.project', 'required':'True'},
    'date_from': {'string':"Start date",'type':'datetime','required':'True' ,'default': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S')},
}

def timeformat_convert(cr, uid, time_string, context={}):
#    Function to convert input time string:: 8.5 to output time string 8:30

        split_list = str(time_string).split('.')
        hour_part = split_list[0]
        mins_part = split_list[1]
        round_mins  = int(round(float(mins_part) * 60,-2))
        converted_string = hour_part + ':' + str(round_mins)[0:2]
        return converted_string

def leaves_resource(cr,uid,id):
#    To get the leaves for the members working on project

        pool = pooler.get_pool(cr.dbname)
        resource_leaves_pool = pool.get('resource.calendar.leaves')
        resource_leave_ids = resource_leaves_pool.search(cr,uid,[('resource_id','=',id)])
        leaves = []
        if resource_leave_ids:
            res_leaves = resource_leaves_pool.read(cr,uid,resource_leave_ids,['date_from','date_to'])
            for leave in range(len(res_leaves)):
                    dt_start = datetime.datetime.strptime(res_leaves[leave]['date_from'],'%Y-%m-%d %H:%M:%S')
                    dt_end = datetime.datetime.strptime(res_leaves[leave]['date_to'],'%Y-%m-%d %H:%M:%S')
                    no = dt_end - dt_start
                    leave_days = no.days + 1
            [leaves.append((dt_start + datetime.timedelta(days=x)).strftime('%Y-%m-%d')) for x in range(int(leave_days))]
            leaves.sort()
        return leaves

class wizard_compute_tasks(wizard.interface):


    def _compute_date(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        project_pool = pool.get('project.project')
        task_pool = pool.get('project.task')
        resource_pool = pool.get('resource.resource')
        resource_leaves_pool = pool.get('resource.calendar.leaves')
        resource_week_pool = pool.get('resource.calendar.week')
        user_pool = pool.get('res.users')

        project_id = data['form']['project_id']
        project = project_pool.browse(cr,uid,project_id)
        task_ids = task_pool.search(cr,uid,[('project_id','=',project_id)])
        if task_ids:
            wktime_cal = []
            leaves = []
            task_ids.sort()
            task_obj = task_pool.browse(cr,uid,task_ids)
            task_1 = task_obj[0]
            date_start = datetime.datetime.strftime(datetime.datetime.strptime(data['form']['date_from'],"%Y-%m-%d %H:%M:%S"),"%Y-%m-%d %H:%M")
            calendar_id = project.resource_calendar_id.id

#     If project has a working calendar then that would be used otherwise
#     the default faces calendar would  be used
            if calendar_id:
                resource_leave_ids = resource_leaves_pool.search(cr,uid,[('calendar_id','=',calendar_id)])
                time_range = "8:00-8:00"
                non_working = ""
                wk = {"0":"mon","1":"tue","2":"wed","3":"thu","4":"fri","5":"sat","6":"sun"}
                wk_days = {}
                wk_time = {}
                wktime_list = []
                week_ids = resource_week_pool.search(cr,uid,[('calendar_id','=',calendar_id)])
                week_obj = resource_week_pool.read(cr,uid,week_ids,['dayofweek','hour_from','hour_to'])

#     Converting time formats into appropriate format required
#     and creating a list like [('mon', '8:00-12:00'), ('mon', '13:00-18:00')]
                for week in week_obj:
                    res_str = ""
                    if wk.has_key(week['dayofweek']):
                        day = wk[week['dayofweek']]
                        wk_days[week['dayofweek']] = wk[week['dayofweek']]
                    hour_from_str = timeformat_convert(cr,uid,week['hour_from'])
                    hour_to_str = timeformat_convert(cr,uid,week['hour_to'])
                    res_str = hour_from_str + '-' + hour_to_str
                    wktime_list.append((day,res_str))

#     Converting it to format like [('mon', '8:00-12:00', '13:00-18:00')]
                for item in wktime_list:
                    if wk_time.has_key(item[0]):
                        wk_time[item[0]].append(item[1])
                    else:
                        wk_time[item[0]] = [item[0]]
                        wk_time[item[0]].append(item[1])

                for k,v in wk_time.items():
                    wktime_cal.append(tuple(v))

#     For non working days adding [('tue,wed,fri,sat,sun', '8:00-8:00')]
                for k,v in wk_days.items():
                    if wk.has_key(k):
                        wk.pop(k)
                for v in wk.itervalues():
                    non_working += v + ','
                if non_working:
                    wktime_cal.append((non_working[:-1],time_range))

#     If project working calendar has any leaves
                if resource_leave_ids:
                    res_leaves = resource_leaves_pool.read(cr,uid,resource_leave_ids,['date_from','date_to'])
                    for leave in range(len(res_leaves)):
                        dt_start = datetime.datetime.strptime(res_leaves[leave]['date_from'],'%Y-%m-%d %H:%M:%S')
                        dt_end = datetime.datetime.strptime(res_leaves[leave]['date_to'],'%Y-%m-%d %H:%M:%S')
                        no = dt_end - dt_start
                        leave_days = no.days + 1
                    [leaves.append((dt_start + datetime.timedelta(days=x)).strftime('%Y-%m-%d')) for x in range(int(leave_days))]
                    leaves.sort()

#    To create resources which are the Project Members
            resource = project.members
            resource_objs = []
            for no in range(len(resource)):
                leaves = []
                resource_eff = 1.00
                resource_id = resource_pool.search(cr,uid,[('user_id','=',resource[no].id)])
                if resource_id:
#    Getting the efficiency for specific resource
                    resource_eff = resource_pool.browse(cr,uid,resource_id)[0].time_efficiency

#   Getting list of leaves for specific resource
                    if wktime_cal:
                        leaves = leaves_resource(cr,uid,resource_id)
                resource_objs.append(classobj(str(resource[no].name),(Resource,),{'__doc__':resource[no].name,'__name__':resource[no].name,'vacation':tuple(leaves),'efficiency':resource_eff}))
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
                if wktime_cal:
                        working_days = wktime_cal
                        vacation = tuple(leaves)

#    Dynamic Creation of tasks
                for i in range(len(task_obj)):
                    hours = str(task_obj[i].remaining_hours / task_obj[i].occupation_rate)+ 'H'
                    if task_obj[i].priority in priority_dict.keys():
                        priorty = priority_dict[task_obj[i].priority]
                    if task_obj[i].user_id:
                       for resource_object in resource_objs:
                            if resource_object.__name__ == task_obj[i].user_id.name:
                               task = tasks_resource(i,hours,priorty,resource_object)
                    else:
                        task = tasks_resource(i,hours,priorty)

            project = BalancedProject(Project)
            loop_no = 0
            for t in project:
                s_date = t.start.to_datetime()
                e_date = t.end.to_datetime()
                if loop_no == 0:
                    project_pool.write(cr,uid,[project_id],{'date':e_date})
                else:
                    user_id = user_pool.search(cr,uid,[('name','=',t.booked_resource[0].__name__)])
                    task_pool.write(cr,uid,[task_obj[loop_no-1].id],{'date_start':s_date,'date_deadline':e_date,'user_id':user_id[0]})
                loop_no +=1

        return {}

    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':compute_form, 'fields':compute_fields, 'state':[
                ('end', 'Cancel'),
                ('compute', 'Compute')
            ]},
        },


        'compute': {
            'actions': [_compute_date],
            'result': {'type':'form','arch':success_msg,'fields':{}, 'state':[('end', 'Ok')]},
        }
    }
wizard_compute_tasks('wizard.compute.tasks')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
