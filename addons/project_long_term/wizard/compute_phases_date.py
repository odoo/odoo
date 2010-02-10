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

compute_form = """<?xml version="1.0" ?>
<form string="Compute Scheduling of Phases">

    <field name="phase_id" colspan="4"/>

</form>"""

compute_fields = {
    'phase_id': {'string':'Phase', 'type':'many2one', 'relation': 'project.phase', 'required':'True'},

}

success_msg = """<?xml version="1.0" ?>
<form string="Compute Scheduling of Phases">
    <label string="Phase Scheduling completed successfully."/>
</form>"""

def timeformat_convert(cr, uid, time_string, context={}):
#    Function to convert input time string:: 8.5 to output time string 8:30

        split_list = str(time_string).split('.')
        hour_part = split_list[0]
        mins_part = split_list[1]
        round_mins  = int(round(float(mins_part) * 60,-2))
        converted_string = hour_part + ':' + str(round_mins)[0:2]
        return converted_string

def leaves_resource(cr,uid,id):
#    To get the leaves for the resource_ids working on phase

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

def resource_list(cr,uid,obj):
#    To get the resource_ids working on phase

        pool = pooler.get_pool(cr.dbname)
        resource_pool = pool.get('resource.resource')
        resources = obj.resource_ids
        resource_objs = []
        for no in range(len(resources)):
            resource_id = resource_pool.search(cr,uid,[('id','=',resources[no].resource_id.id)])
            if resource_id:
            #   Getting list of leaves for specific resource
                leaves = leaves_resource(cr,uid,resource_id)
            #   Creating the faces.Resource object with resource specific efficiency and vacation
                resource_objs.append(classobj(str(resources[no].resource_id.name),(Resource,),{'__doc__':resources[no].resource_id.name,'__name__':resources[no].resource_id.name,'efficiency':resources[no].useability/100,'vacation':tuple(leaves)}))
        return resource_objs

class wizard_compute_phases(wizard.interface):

    def _compute_date(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        project_pool = pool.get('project.project')
        phase_pool = pool.get('project.phase')
        resource_pool = pool.get('resource.resource')
        resource_leaves_pool = pool.get('resource.calendar.leaves')
        resource_week_pool = pool.get('resource.calendar.week')
        avg_hr = 0.0
        wktime_cal = []
        leaves = []
        phase_id = data['form']['phase_id']
        phase = phase_pool.browse(cr,uid,phase_id)
        calendar_id = phase.project_id.resource_calendar_id.id

#     If project has a working calendar then that would be used otherwise
#     the default faces calendar would  be used
        if calendar_id:
            time_range = "8:00-8:00"
            non_working = ""
            wk = {"0":"mon","1":"tue","2":"wed","3":"thu","4":"fri","5":"sat","6":"sun"}
            wk_days = {}
            wk_time = {}
            wktime_list = []
            hours = []
            hr = 0
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
                hours.append(week['hour_from'])
                hours.append(week['hour_to'])
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

            for hour in range(len(hours)):
                if hour%2 ==0:
                    hr += float(hours[hour+1]) - float(hours[hour])
            avg_hr = hr/len(wktime_cal)

#     For non working days adding [('tue,wed,fri,sat,sun', '8:00-8:00')]
            for k,v in wk_days.items():
                if wk.has_key(k):
                    wk.pop(k)
            for v in wk.itervalues():
                non_working += v + ','
            if non_working:
                wktime_cal.append((non_working[:-1],time_range))

#     If project working calendar has any leaves
            resource_leave_ids = resource_leaves_pool.search(cr,uid,[('calendar_id','=',calendar_id)])
            if resource_leave_ids:
                res_leaves = resource_leaves_pool.read(cr,uid,resource_leave_ids,['date_from','date_to'])
                for leave in range(len(res_leaves)):
                    dt_start = datetime.datetime.strptime(res_leaves[leave]['date_from'],'%Y-%m-%d %H:%M:%S')
                    dt_end = datetime.datetime.strptime(res_leaves[leave]['date_to'],'%Y-%m-%d %H:%M:%S')
                    no = dt_end - dt_start
                    leave_days = no.days + 1
                [leaves.append((dt_start + datetime.timedelta(days=x)).strftime('%Y-%m-%d')) for x in range(int(leave_days))]
                leaves.sort()


        def phase_schedule(cr,uid,phase,start_date,avg_hour = 0.0):
           if phase:

                #    To get resources and the duration for the phase
                resources_list = resource_list(cr,uid,phase)
                if not avg_hour:
                    avg_hour = 8.0
                man_days = str(phase.duration * avg_hour) + 'H'

                #    Creating a new project for each phase
                def Project():
                    start = start_date

                    #    If project has working calendar else the default one would be considered
                    if wktime_cal or leaves:
                        working_days = wktime_cal
                        vacation = tuple(leaves)

                    def phase():
                        effort = man_days
                        resource = reduce(operator.or_,resources_list)

                project = BalancedProject(Project)
                print 'Project Phase Start & End:::',project.phase.name,project.phase.booked_resource,project.phase.start.to_datetime(),project.phase.end.to_datetime()
                s_date = project.phase.start.to_datetime()
                e_date = project.phase.end.to_datetime()

                #    According to constraints on date start and date end on phase recalculation done
                if phase.constraint_date_start and str(s_date) < phase.constraint_date_start:
                    start_date = phase.constraint_date_start
                else:
                    start_date = s_date
                if phase.constraint_date_end and str(e_date) > phase.constraint_date_end:
                    end_date = phase.constraint_date_end[:-3]
                else:
                    end_date = e_date

                #    Writing the dates back
                phase_pool.write(cr,uid,[phase.id],{'date_start':start_date,'date_end':end_date})
                date_start = end_date

                #    Recursive calling the next phases till all the phases are scheduled
                for phase in phase.next_phase_ids:
                   phase_schedule(cr,uid,phase,date_start)

        #    Phase Scheduling starts from here with the call to phase_schedule method
        start_dt = datetime.datetime.strftime((datetime.datetime.strptime(phase.project_id.date_start,"%Y-%m-%d")),"%Y-%m-%d %H:%M")
        if avg_hr:
            phase_schedule(cr,uid,phase,start_dt,avg_hr)
        else:
            phase_schedule(cr,uid,phase,start_dt)

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
wizard_compute_phases('wizard.compute.phases')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
