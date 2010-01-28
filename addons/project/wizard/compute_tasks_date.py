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
from resource.faces_new import *

compute_form = """<?xml version="1.0" ?>
<form string="Compute Scheduling of Tasks">

    <field name="project_id" colspan="4"/>

</form>"""

compute_fields = {
    'project_id': {'string':'Project', 'type':'many2one', 'relation': 'project.project', 'required':'True'},

}
def timeformat_convert(cr, uid, time_string, context={}):
        strg = str(time_string)[-2:]
        last_strg = str(time_string)[0:-2]
        if strg != '.0':
            if '.' not in strg:
                strg = '.' + strg
                last_strg = str(time_string)[:-3]

            new_strg = round(float(strg) / 0.016666667)
            converted_strg = last_strg + ':' + str(new_strg)[:-2]
        else:
            converted_strg = last_strg + ':00'

        return converted_strg

class wizard_compute_tasks(wizard.interface):

    def _compute_date(self, cr, uid, data, context):

        project_id = data['form']['project_id']
        project = pooler.get_pool(cr.dbname).get('project.project').browse(cr,uid,project_id)
        task_ids = pooler.get_pool(cr.dbname).get('project.task').search(cr,uid,[('project_id','=',project_id)])
        if task_ids:
            task_obj = pooler.get_pool(cr.dbname).get('project.task').browse(cr,uid,task_ids)
            task_1 = task_obj[0]
            if task_1.date_start:
                date_dt = datetime.datetime.strptime(task_1.date_start,"%Y-%m-%d %H:%M:%S")
            else:
                date_dt = datetime.datetime.strptime(project.date_start,"%Y-%m-%d")
            print 'Start Date of Project:::',date_dt
            pdt = datetime.datetime.strftime(date_dt,"%Y-%m-%d %H:%M")

            class user(Resource):
                 pass

            for i in range(len(task_obj)):
                final_lst = []
                leaves = []
                if task_obj[i].user_id.id:
                    resource_id = pooler.get_pool(cr.dbname).get('resource.resource').search(cr,uid,[('user_id','=',task_obj[i].user_id.id)])
                    resource_obj = pooler.get_pool(cr.dbname).get('resource.resource').browse(cr,uid,resource_id)[0]
                    if resource_obj.calendar_id:
                        time_range = "8:00-8:00"
                        b = ""
                        wk = {"0":"mon","1":"tue","2":"wed","3":"thu","4":"fri"}
                        wk_days = {}
                        wk_time = {}
                        tlist = []
                        week_ids = pooler.get_pool(cr.dbname).get('resource.calendar.week').search(cr,uid,[('calendar_id','=',resource_obj.calendar_id.id)])
                        week_obj = pooler.get_pool(cr.dbname).get('resource.calendar.week').read(cr,uid,week_ids,['dayofweek','hour_from','hour_to'])

                        for week in week_obj:
                            res_str = ""
                            if wk.has_key(week['dayofweek']):
                                day = wk[week['dayofweek']]
                                wk_days[week['dayofweek']] = wk[week['dayofweek']]

                            hour_from_str = timeformat_convert(cr,uid,week['hour_from'])
                            hour_to_str = timeformat_convert(cr,uid,week['hour_to'])
                            res_str = hour_from_str + '-' + hour_to_str
                            tlist.append((day,res_str))

                        for item in tlist:
                            if wk_time.has_key(item[0]):
                                wk_time[item[0]].append(item[1])
                            else:
                                wk_time[item[0]] = [item[0]]
                                wk_time[item[0]].append(item[1])

                        for k,v in wk_time.items():
                            final_lst.append(tuple(v))
                        print 'final Dictionary List:::',final_lst

                        for k,v in wk_days.items():
                            if wk.has_key(k):
                                wk.pop(k)
                        for v in wk.itervalues():
                            b += v + ','
                        final_lst.append((b[:-1],time_range))
                        print 'Final Tlist:::',tlist

                        resource_leave_ids = pooler.get_pool(cr.dbname).get('resource.calendar.leaves').search(cr,uid,[('resource_id','=',resource_id)])
                        if resource_leave_ids:
                            res_leaves = pooler.get_pool(cr.dbname).get('resource.calendar.leaves').read(cr,uid,resource_leave_ids,['date_from','date_to'])
                            for leave in range(len(res_leaves)):
                                dt_start = datetime.datetime.strptime(res_leaves[leave]['date_from'],'%Y-%m-%d %H:%M:%S')
                                dt_end = datetime.datetime.strptime(res_leaves[leave]['date_to'],'%Y-%m-%d %H:%M:%S')
                                no = dt_end - dt_start
                                leave_days = no.days + 1
                            [leaves.append((dt_start + datetime.timedelta(days=x)).strftime('%Y-%m-%d')) for x in range(int(leave_days))]
                            leaves.sort()
                            print 'Dt_leaves::',leaves


                hours = task_obj[i].remaining_hours / task_obj[i].occupation_rate
                hours = str(hours)[:-2] + 'H'
                print 'Hours:::',hours
                if i == 0:
                    ndt = pdt
                else:
                    data = pooler.get_pool(cr.dbname).get('project.task').read(cr,uid,[task_obj[i-1].id],['date_end'])[0]
                    ndt = data['date_end'][0:16]

                def Project_1():
                    resource = user
                    title = project.name
                    start = ndt
                    effort = hours

                    if final_lst or leaves:
                        working_days = final_lst
                        vacation = tuple(leaves)

                    def task1():
                        start = ndt
                        effort = hours
                        title = task_obj[i].name

                project_1 = BalancedProject(Project_1)
                s_date = project_1.calendar.WorkingDate(project_1.task1.start).to_datetime()
                e_date = project_1.calendar.WorkingDate(project_1.task1.end).to_datetime()
                print 'Start Date::::',s_date,task_obj[i].name
                print 'End Date::::',e_date,task_obj[i].name
                pooler.get_pool(cr.dbname).get('project.task').write(cr,uid,[task_obj[i].id],{'date_start':s_date,'date_end':e_date})

        return {}
    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':compute_form, 'fields':compute_fields, 'state':[
                ('end', 'Cancel'),
                ('ok', 'Ok')

            ]},
        },
        'ok': {
            'actions': [_compute_date],
            'result': {'type':'state', 'state':'end'},
        }
    }
wizard_compute_tasks('wizard.compute.tasks')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

