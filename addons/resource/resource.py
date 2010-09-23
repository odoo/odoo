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
import time
import math

from osv import fields, osv
from tools.translate import _

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

    def _get_leaves(self, cr, uid, id, resource):
        resource_cal_leaves = self.pool.get('resource.calendar.leaves')
        dt_leave = []

        resource_leave_ids = resource_cal_leaves.search(cr, uid, [('calendar_id','=',id), '|', ('resource_id','=',False), ('resource_id','=',resource)])
        res_leaves = resource_cal_leaves.read(cr, uid, resource_leave_ids, ['date_from', 'date_to'])

        for leave in res_leaves:
            dtf = datetime.strptime(leave['date_from'], '%Y-%m-%d %H:%M:%S')
            dtt = datetime.strptime(leave['date_to'], '%Y-%m-%d %H:%M:%S')
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
        cycle = 0
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

    def interval_get(self, cr, uid, id, dt_from, hours, resource=False, byday=True):
        if not id:
            td = int(hours)*3
            return [(dt_from, dt_from + timedelta(hours=td))]
        dt_leave = self._get_leaves(cr, uid, id, resource)
        todo = hours
        cycle = 0
        result = []
        maxrecur = 100
        current_hour = dt_from.hour
        while (todo>0) and maxrecur:
            cr.execute("select hour_from,hour_to from resource_calendar_attendance where dayofweek='%s' and calendar_id=%s order by hour_from", (dt_from.weekday(),id))
            for (hour_from,hour_to) in cr.fetchall():
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
        return result

    def interval_hours_get(self, cr, uid, id, dt_from, dt_to, resource=False):
        result = []
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
        'hour_from' : fields.float('Work from', size=8, required=True),
        'hour_to' : fields.float("Work to", size=8, required=True),
        'calendar_id' : fields.many2one("resource.calendar", "Resource's Calendar", required=True),
    }
    _order = 'dayofweek, hour_from'
resource_calendar_attendance()

class resource_resource(osv.osv):
    _name = "resource.resource"
    _description = "Resource Detail"
    _columns = {
        'name' : fields.char("Name", size=64, required=True),
        'code': fields.char('Code', size=16),
        'active' : fields.boolean('Active', help="If the active field is set to true, it will allow you to hide the resource record without removing it."),
        'company_id' : fields.many2one('res.company', 'Company'),
        'resource_type': fields.selection([('user','Human'),('material','Material')], 'Resource Type', required=True),
        'user_id' : fields.many2one('res.users', 'User', help='Related user name for the resource to manage its access.'),
        'time_efficiency' : fields.float('Efficiency factor', size=8, required=True, help="This field depict the efficiency of the resource to complete tasks. e.g  resource put alone on a phase of 5 days with 5 tasks assigned to him, will show a load of 100% for this phase by default, but if we put a efficency of 200%, then his load will only be 50%."),
        'calendar_id' : fields.many2one("resource.calendar", "Working time", help="Define the schedule of resource"),
    }
    _defaults = {
        'resource_type' : 'user',
        'time_efficiency' : 1,
        'active' : True,
        'company_id': lambda self, cr, uid, context: self.pool.get('res.company')._company_default_get(cr, uid, 'resource.resource', context=context)
    }

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}

        if context.get('project_id',False):
            project_pool = self.pool.get('project.project')
            project_rec = project_pool.browse(cr, uid, context['project_id'])
            user_ids = [user_id.id for user_id in project_rec.members]
            args.append(('user_id','in',user_ids))

        return super(resource_resource, self).search(cr, uid, args, offset, limit, order, context, count)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        if not default.get('name', False):
            default['name'] = self.browse(cr, uid, id, context=context).name + _(' (copy)')
        return super(resource_resource, self).copy(cr, uid, id, default, context)

resource_resource()

class resource_calendar_leaves(osv.osv):
    _name = "resource.calendar.leaves"
    _description = "Leave Detail"
    _columns = {
        'name' : fields.char("Name", size=64),
        'company_id' : fields.related('calendar_id','company_id',type='many2one',relation='res.company',string="Company",readonly=True),
        'calendar_id' : fields.many2one("resource.calendar", "Working time"),
        'date_from' : fields.datetime('Start Date', required=True),
        'date_to' : fields.datetime('End Date', required=True),
        'resource_id' : fields.many2one("resource.resource", "Resource", help="If empty, this is a generic holiday for the company. If a resource is set, the holiday/leave is only for this resource"),
    }

    def check_dates(self, cr, uid, ids, context={}):
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
            result['calendar_id'] = resource_pool.browse(cr, uid, resource).calendar_id.id
            return {'value': result}
        return {'value': {'calendar_id': []}}

resource_calendar_leaves()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: