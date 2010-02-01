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

class wizard_compute_phases(wizard.interface):

    def _compute_date(self, cr, uid, data, context):
        project_id = data['form']['project_id']
        project = pooler.get_pool(cr.dbname).get('project.project').browse(cr,uid,project_id)
        phase_ids = pooler.get_pool(cr.dbname).get('project.phase').search(cr,uid,[('project_id','=',project_id)])
        if phase_ids:
            phase_obj = pooler.get_pool(cr.dbname).get('project.phase').browse(cr,uid,phase_ids)
            phase_1 = phase_obj[0]
            if phase_1.date_start:
                date_dt = datetime.datetime.strptime(phase_1.date_start,"%Y-%m-%d %H:%M:%S")
            else:
                date_dt = datetime.datetime.strptime(project.date_start,"%Y-%m-%d")
            dt = datetime.datetime.strftime(date_dt,"%Y-%m-%d %H:%M")

            for i in range(len(phase_obj)):
                final_lst = []
                leaves = []
#                if phase_obj[i].user_id.id:
#                    resource_id = pooler.get_pool(cr.dbname).get('resource.resource').search(cr,uid,[('user_id','=',task_obj[i].user_id.id)])
#                    resource_obj = pooler.get_pool(cr.dbname).get('resource.resource').browse(cr,uid,resource_id)[0]
                if project.resource_calendar_id:
                        non_working = ""
                        time_range = "8:00-8:00"
                        wk = {"0":"mon","1":"tue","2":"wed","3":"thu","4":"fri"}
                        wk_days = {}
                        wk_time = {}
                        tlist = []
                        hours = []
                        hr = 0

                        week_ids = pooler.get_pool(cr.dbname).get('resource.calendar.week').search(cr,uid,[('calendar_id','=',project.resource_calendar_id.id)])
                        week_obj = pooler.get_pool(cr.dbname).get('resource.calendar.week').read(cr,uid,week_ids,['dayofweek','hour_from','hour_to'])

                        for week in week_obj:
                            res_str = ""
                            if wk.has_key(week['dayofweek']):
                                day = wk[week['dayofweek']]
                                wk_days[week['dayofweek']] = wk[week['dayofweek']]

                            hour_from_str = timeformat_convert(cr,uid,week['hour_from'])
                            hour_to_str = timeformat_convert(cr,uid,week['hour_to'])
                            hours.append(week['hour_from'])
                            hours.append(week['hour_to'])
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

                        for k,v in wk_days.items():
                            if wk.has_key(k):
                                wk.pop(k)
                        for v in wk.itervalues():
                            non_working += v + ','
                        if non_working:
                            final_lst.append((non_working[:-1],time_range))

                        leave_ids = pooler.get_pool(cr.dbname).get('resource.calendar.leaves').search(cr,uid,[('calendar_id','=',project.resource_calendar_id.id)])
                        if leave_ids:
                            res_leaves = pooler.get_pool(cr.dbname).get('resource.calendar.leaves').read(cr,uid,leave_ids,['date_from','date_to'])
                            for leave in range(len(res_leaves)):
                                dt_start = datetime.datetime.strptime(res_leaves[leave]['date_from'],'%Y-%m-%d %H:%M:%S')
                                dt_end = datetime.datetime.strptime(res_leaves[leave]['date_to'],'%Y-%m-%d %H:%M:%S')
                                no = dt_end - dt_start
                                leave_days = no.days + 1
                            [leaves.append((dt_start + datetime.timedelta(days=x)).strftime('%Y-%m-%d')) for x in range(int(leave_days))]
                            leaves.sort()

                        for hour in range(0,4):
                            if hour%2 ==0:
                                hr += float(hours[hour+1]) - float(hours[hour])

                man_days = str(phase_obj[i].duration * hr)[:-2] + 'H'

                if i == 0:
                    new_dt = dt
                else:
                    data = pooler.get_pool(cr.dbname).get('project.phase').read(cr,uid,[phase_obj[i-1].id],['date_end'])[0]
                    if phase_obj[i].constraint_date_start and data['date_end'] < phase_obj[i].constraint_date_start:
                        new_dt = phase_obj[i].constraint_date_start[0:16]
                    else:
                        new_dt = data['date_end'][0:16]

                class user(Resource):
                 pass

                def Project_1():
                    resource = user
                    title = project.name
                    start = new_dt
                    effort = man_days

                    if final_lst or leaves:
                        working_days = final_lst
                        vacation = tuple(leaves)

                    def phase1():
                        start = new_dt
                        effort = man_days
                        title = phase_obj[i].name

                project_1 = BalancedProject(Project_1)
                start_date = project_1.calendar.WorkingDate(project_1.phase1.start).to_datetime()
                e_date = project_1.calendar.WorkingDate(project_1.phase1.end).to_datetime()
                if phase_obj[i].constraint_date_end and str(e_date) > phase_obj[i].constraint_date_end:
                    end_date = phase_obj[i].constraint_date_end
                else:
                    end_date = e_date

                pooler.get_pool(cr.dbname).get('project.phase').write(cr,uid,[phase_obj[i].id],{'date_start':start_date,'date_end':end_date})

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
wizard_compute_phases('wizard.compute.phases')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

