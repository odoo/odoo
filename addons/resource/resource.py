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

from datetime import datetime, timedelta
import math
from faces import *
from new import classobj
from osv import fields, osv
from tools.translate import _

from itertools import groupby
from operator import itemgetter


class resource_calendar(osv.osv):
    _name = "resource.calendar"
    _description = "Resource Calendar"
    _columns = {
        'name' : fields.char("Name", size=64, required=True),
        'company_id' : fields.many2one('res.company', 'Company', required=False),
        'attendance_ids' : fields.one2many('resource.calendar.attendance', 'calendar_id', 'Working Time'),
        'manager' : fields.many2one('res.users', 'Workgroup manager'),
    }
    _defaults = {
        'company_id': lambda self, cr, uid, context: self.pool.get('res.company')._company_default_get(cr, uid, 'resource.calendar', context=context)
    }

    def working_hours_on_day(self, cr, uid, resource_calendar_id, day, context=None):
        """
        @param resource_calendar_id: resource.calendar browse record
        @param day: datetime object
        @return: returns the working hours (as float) men should work on the given day if is in the attendance_ids of the resource_calendar_id (i.e if that day is a working day), returns 0.0 otherwise
        """
        res = 0.0
        for working_day in resource_calendar_id.attendance_ids:
            if (int(working_day.dayofweek) + 1) == day.isoweekday():
                res += working_day.hour_to - working_day.hour_from
        return res 

    def _get_leaves(self, cr, uid, id, resource):
        resource_cal_leaves = self.pool.get('resource.calendar.leaves')
        dt_leave = []

        resource_leave_ids = resource_cal_leaves.search(cr, uid, [('calendar_id','=',id), '|', ('resource_id','=',False), ('resource_id','=',resource)])
        #res_leaves = resource_cal_leaves.read(cr, uid, resource_leave_ids, ['date_from', 'date_to'])
        res_leaves = resource_cal_leaves.browse(cr, uid, resource_leave_ids)

        for leave in res_leaves:
            dtf = datetime.strptime(leave.date_from, '%Y-%m-%d %H:%M:%S')
            dtt = datetime.strptime(leave.date_to, '%Y-%m-%d %H:%M:%S')
            no = dtt - dtf
            [dt_leave.append((dtf + timedelta(days=x)).strftime('%Y-%m-%d')) for x in range(int(no.days + 1))]
            dt_leave.sort()

        return dt_leave

    def interval_min_get(self, cr, uid, id, dt_from, hours, resource=False):
        if not id:
            td = int(hours)*3
            return [(dt_from - timedelta(hours=td), dt_from)]
        dt_leave = self._get_leaves(cr, uid, id, resource)
        dt_leave.reverse()
        todo = hours
        result = []
        maxrecur = 100
        current_hour = dt_from.hour
        while (todo>0) and maxrecur:
            cr.execute("select hour_from,hour_to from resource_calendar_attendance where dayofweek='%s' and calendar_id=%s order by hour_from desc", (dt_from.weekday(),id))
            for (hour_from,hour_to) in cr.fetchall():
                leave_flag  = False
                if (hour_from<current_hour) and (todo>0):
                    m = min(hour_to, current_hour)
                    if (m-hour_from)>todo:
                        hour_from = m-todo
                    dt_check = dt_from.strftime('%Y-%m-%d')
                    for leave in dt_leave:
                        if dt_check == leave:
                            dt_check = datetime.strptime(dt_check, '%Y-%m-%d') + timedelta(days=1)
                            leave_flag = True
                    if leave_flag:
                        break
                    else:
                        d1 = datetime(dt_from.year, dt_from.month, dt_from.day, int(math.floor(hour_from)), int((hour_from%1) * 60))
                        d2 = datetime(dt_from.year, dt_from.month, dt_from.day, int(math.floor(m)), int((m%1) * 60))
                        result.append((d1, d2))
                        current_hour = hour_from
                        todo -= (m-hour_from)
            dt_from -= timedelta(days=1)
            current_hour = 24
            maxrecur -= 1
        result.reverse()
        return result

    # def interval_get(self, cr, uid, id, dt_from, hours, resource=False, byday=True):
    def interval_get_multi(self, cr, uid, date_and_hours_by_cal, resource=False, byday=True):
        def group(lst, key):
            lst.sort(key=itemgetter(key))
            grouped = groupby(lst, itemgetter(key))
            return dict([(k, [v for v in itr]) for k, itr in grouped])
        # END group

        cr.execute("select calendar_id, dayofweek, hour_from, hour_to from resource_calendar_attendance order by hour_from")
        hour_res = cr.dictfetchall()
        hours_by_cal = group(hour_res, 'calendar_id')

        results = {}

        for d, hours, id in date_and_hours_by_cal:
            dt_from = datetime.strptime(d, '%Y-%m-%d %H:%M:%S')
            if not id:
                td = int(hours)*3
                results[(d, hours, id)] = [(dt_from, dt_from + timedelta(hours=td))]
                continue

            dt_leave = self._get_leaves(cr, uid, id, resource)
            todo = hours
            result = []
            maxrecur = 100
            current_hour = dt_from.hour
            while (todo>0) and maxrecur:
                for (hour_from,hour_to) in [(item['hour_from'], item['hour_to']) for item in hours_by_cal[id] if item['dayofweek'] == str(dt_from.weekday())]:
                    leave_flag  = False
                    if (hour_to>current_hour) and (todo>0):
                        m = max(hour_from, current_hour)
                        if (hour_to-m)>todo:
                            hour_to = m+todo
                        dt_check = dt_from.strftime('%Y-%m-%d')
                        for leave in dt_leave:
                            if dt_check == leave:
                                dt_check = datetime.strptime(dt_check, '%Y-%m-%d') + timedelta(days=1)
                                leave_flag = True
                        if leave_flag:
                            break
                        else:
                            d1 = datetime(dt_from.year, dt_from.month, dt_from.day, int(math.floor(m)), int((m%1) * 60))
                            d2 = datetime(dt_from.year, dt_from.month, dt_from.day, int(math.floor(hour_to)), int((hour_to%1) * 60))
                            result.append((d1, d2))
                            current_hour = hour_to
                            todo -= (hour_to - m)
                dt_from += timedelta(days=1)
                current_hour = 0
                maxrecur -= 1
            results[(d, hours, id)] = result
        return results

    def interval_get(self, cr, uid, id, dt_from, hours, resource=False, byday=True):
        res = self.interval_get_multi(cr, uid, [(dt_from.strftime('%Y-%m-%d %H:%M:%S'), hours, id)], resource, byday)[(dt_from.strftime('%Y-%m-%d %H:%M:%S'), hours, id)]
        return res

    def interval_hours_get(self, cr, uid, id, dt_from, dt_to, resource=False):
        if not id:
            return 0.0
        dt_leave = self._get_leaves(cr, uid, id, resource)
        hours = 0.0

        current_hour = dt_from.hour

        while (dt_from <= dt_to):
            cr.execute("select hour_from,hour_to from resource_calendar_attendance where dayofweek='%s' and calendar_id=%s order by hour_from", (dt_from.weekday(),id))
            der =  cr.fetchall()
            for (hour_from,hour_to) in der:
                if hours != 0.0:#For first time of the loop only,hours will be 0
                    current_hour = hour_from
                leave_flag = False
                if (hour_to>=current_hour):
                    dt_check = dt_from.strftime('%Y-%m-%d')
                    for leave in dt_leave:
                        if dt_check == leave:
                            dt_check = datetime.strptime(dt_check, "%Y-%m-%d") + timedelta(days=1)
                            leave_flag = True

                    if leave_flag:
                        break
                    else:
                        d1 = dt_from
                        d2 = datetime(dt_from.year, dt_from.month, dt_from.day, int(math.floor(hour_to)), int((hour_to%1) * 60))

                        if hours != 0.0:#For first time of the loop only,hours will be 0
                            d1 = datetime(dt_from.year, dt_from.month, dt_from.day, int(math.floor(current_hour)), int((current_hour%1) * 60))

                        if dt_from.day == dt_to.day:
                            if hour_from <= dt_to.hour <= hour_to:
                                d2 = dt_to
                        dt_from = d2
                        hours += (d2-d1).seconds
            dt_from = datetime(dt_from.year, dt_from.month, dt_from.day, int(math.floor(current_hour)), int((current_hour%1) * 60)) + timedelta(days=1)
            current_hour = 0.0

        return (hours/3600)

resource_calendar()

class resource_calendar_attendance(osv.osv):
    _name = "resource.calendar.attendance"
    _description = "Work Detail"
    _columns = {
        'name' : fields.char("Name", size=64, required=True),
        'dayofweek': fields.selection([('0','Monday'),('1','Tuesday'),('2','Wednesday'),('3','Thursday'),('4','Friday'),('5','Saturday'),('6','Sunday')], 'Day of week'),
        'date_from' : fields.date('Starting date'),
        'hour_from' : fields.float('Work from', size=8, required=True, help="Working time will start from"),
        'hour_to' : fields.float("Work to", size=8, required=True, help="Working time will end at"),
        'calendar_id' : fields.many2one("resource.calendar", "Resource's Calendar", required=True),
    }
    _order = 'dayofweek, hour_from'
resource_calendar_attendance()

def convert_timeformat(time_string):
    split_list = str(time_string).split('.')
    hour_part = split_list[0]
    mins_part = split_list[1]
    round_mins = int(round(float(mins_part) * 60,-2))
    converted_string = hour_part + ':' + str(round_mins)[0:2]
    return converted_string

class resource_resource(osv.osv):
    _name = "resource.resource"
    _description = "Resource Detail"
    _columns = {
        'name' : fields.char("Name", size=64, required=True),
        'code': fields.char('Code', size=16),
        'active' : fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the resource record without removing it."),
        'company_id' : fields.many2one('res.company', 'Company'),
        'resource_type': fields.selection([('user','Human'),('material','Material')], 'Resource Type', required=True),
        'user_id' : fields.many2one('res.users', 'User', help='Related user name for the resource to manage its access.'),
        'time_efficiency' : fields.float('Efficiency factor', size=8, required=True, help="This field depict the efficiency of the resource to complete tasks. e.g  resource put alone on a phase of 5 days with 5 tasks assigned to him, will show a load of 100% for this phase by default, but if we put a efficency of 200%, then his load will only be 50%."),
        'calendar_id' : fields.many2one("resource.calendar", "Working Period", help="Define the schedule of resource"),
    }
    _defaults = {
        'resource_type' : 'user',
        'time_efficiency' : 1,
        'active' : True,
        'company_id': lambda self, cr, uid, context: self.pool.get('res.company')._company_default_get(cr, uid, 'resource.resource', context=context)
    }

    
    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        if not default.get('name', False):
            default['name'] = self.browse(cr, uid, id, context=context).name + _(' (copy)')
        return super(resource_resource, self).copy(cr, uid, id, default, context)

    def generate_resources(self, cr, uid, user_ids, calendar_id, context=None):
        """
        Return a list of  Resource Class objects for the resources allocated to the phase.
        """
        resource_objs = {}
        user_pool = self.pool.get('res.users')
        for user in user_pool.browse(cr, uid, user_ids, context=context):
            resource_ids = self.search(cr, uid, [('user_id', '=', user.id)], context=context)
            #assert len(resource_ids) < 1, "User should not has more than one resources"
            leaves = []
            resource_eff = 1.0
            if resource_ids:
                for resource in self.browse(cr, uid, resource_ids, context=context):
                    resource_eff = resource.time_efficiency
                    resource_cal = resource.calendar_id.id
                    if resource_cal:
                        leaves = self.compute_vacation(cr, uid, calendar_id, resource.id, resource_cal, context=context)
                    temp = {
                             'name' : resource.name,
                             'vacation': tuple(leaves),
                             'efficiency': resource_eff,
                          }
                    resource_objs[resource.id] = temp     
#            resource_objs.append(classobj(str(user.name), (Resource,),{
#                                             '__doc__': user.name,
#                                             '__name__': user.name,
#                                             'vacation': tuple(leaves),
#                                             'efficiency': resource_eff,
#                                          }))
        return resource_objs

    def compute_vacation(self, cr, uid, calendar_id, resource_id=False, resource_calendar=False, context=None):
        """
        Compute the vacation from the working calendar of the resource.
        @param calendar_id : working calendar of the project
        @param resource_id : resource working on phase/task
        @param resource_calendar : working calendar of the resource
        """
        resource_calendar_leaves_pool = self.pool.get('resource.calendar.leaves')
        leave_list = []
        if resource_id:
            leave_ids = resource_calendar_leaves_pool.search(cr, uid, ['|', ('calendar_id', '=', calendar_id),
                                                                       ('calendar_id', '=', resource_calendar),
                                                                       ('resource_id', '=', resource_id)
                                                                      ], context=context)
        else:
            leave_ids = resource_calendar_leaves_pool.search(cr, uid, [('calendar_id', '=', calendar_id),
                                                                      ('resource_id', '=', False)
                                                                      ], context=context)
        leaves = resource_calendar_leaves_pool.read(cr, uid, leave_ids, ['date_from', 'date_to'], context=context)
        for i in range(len(leaves)):
            dt_start = datetime.strptime(leaves[i]['date_from'], '%Y-%m-%d %H:%M:%S')
            dt_end = datetime.strptime(leaves[i]['date_to'], '%Y-%m-%d %H:%M:%S')
            no = dt_end - dt_start
            [leave_list.append((dt_start + timedelta(days=x)).strftime('%Y-%m-%d')) for x in range(int(no.days + 1))]
            leave_list.sort()
        return leave_list

    def compute_working_calendar(self, cr, uid, calendar_id=False, context=None):
        """
        Change the format of working calendar from 'Openerp' format to bring it into 'Faces' format.
        @param calendar_id : working calendar of the project
        """
        if not calendar_id:
            # Calendar is not specified: working days: 24/7
            return [('fri', '1:0-12:0','12:0-24:0'), ('thu', '1:0-12:0','12:0-24:0'), ('wed', '1:0-12:0','12:0-24:0'), 
                   ('mon', '1:0-12:0','12:0-24:0'), ('tue', '1:0-12:0','12:0-24:0'), ('sat', '1:0-12:0','12:0-24:0'), ('sun', '1:0-12:0','12:0-24:0')]
        resource_attendance_pool = self.pool.get('resource.calendar.attendance')
        time_range = "8:00-8:00"
        non_working = ""
        week_days = {"0": "mon", "1": "tue", "2": "wed","3": "thu", "4": "fri", "5": "sat", "6": "sun"}
        wk_days = {}
        wk_time = {}
        wktime_list = []
        wktime_cal = []
        week_ids = resource_attendance_pool.search(cr, uid, [('calendar_id', '=', calendar_id)], context=context)
        weeks = resource_attendance_pool.read(cr, uid, week_ids, ['dayofweek', 'hour_from', 'hour_to'], context=context)
        # Convert time formats into appropriate format required
        # and create a list like [('mon', '8:00-12:00'), ('mon', '13:00-18:00')]
        for week in weeks:
            res_str = ""
            day = None
            if week_days.has_key(week['dayofweek']):
                day = week_days[week['dayofweek']]
                wk_days[week['dayofweek']] = week_days[week['dayofweek']]
            hour_from_str = convert_timeformat(week['hour_from'])
            hour_to_str = convert_timeformat(week['hour_to'])
            res_str = hour_from_str + '-' + hour_to_str
            wktime_list.append((day, res_str))
        # Convert into format like [('mon', '8:00-12:00', '13:00-18:00')]
        for item in wktime_list:
            if wk_time.has_key(item[0]):
                wk_time[item[0]].append(item[1])
            else:
                wk_time[item[0]] = [item[0]]
                wk_time[item[0]].append(item[1])
        for k,v in wk_time.items():
            wktime_cal.append(tuple(v))
        # Add for the non-working days like: [('sat, sun', '8:00-8:00')]
        for k, v in wk_days.items():
            if week_days.has_key(k):
                week_days.pop(k)
        for v in week_days.itervalues():
            non_working += v + ','
        if non_working:
            wktime_cal.append((non_working[:-1], time_range))
        return wktime_cal

    #TODO: Write optimized alogrothem for resource availability. : Method Yet not implemented
    def check_availability(self, cr, uid, ids, start, end, context=None):
        if context ==  None:
            contex = {}
        allocation = {}
        return allocation

resource_resource()

class resource_calendar_leaves(osv.osv):
    _name = "resource.calendar.leaves"
    _description = "Leave Detail"
    _columns = {
        'name' : fields.char("Name", size=64),
        'company_id' : fields.related('calendar_id','company_id',type='many2one',relation='res.company',string="Company", store=True, readonly=True),
        'calendar_id' : fields.many2one("resource.calendar", "Working time"),
        'date_from' : fields.datetime('Start Date', required=True),
        'date_to' : fields.datetime('End Date', required=True),
        'resource_id' : fields.many2one("resource.resource", "Resource", help="If empty, this is a generic holiday for the company. If a resource is set, the holiday/leave is only for this resource"),
    }

    def check_dates(self, cr, uid, ids, context=None):
         leave = self.read(cr, uid, ids[0], ['date_from', 'date_to'])
         if leave['date_from'] and leave['date_to']:
             if leave['date_from'] > leave['date_to']:
                 return False
         return True

    _constraints = [
        (check_dates, 'Error! leave start-date must be lower then leave end-date.', ['date_from', 'date_to'])
    ]

    def onchange_resource(self,cr, uid, ids, resource, context=None):
        result = {}
        if resource:
            resource_pool = self.pool.get('resource.resource')
            result['calendar_id'] = resource_pool.browse(cr, uid, resource, context=context).calendar_id.id
            return {'value': result}
        return {'value': {'calendar_id': []}}

resource_calendar_leaves()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
