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
import mx.DateTime
import time
import math

from osv import fields, osv
from tools.translate import _

class resource_calendar(osv.osv):
    _name = "resource.calendar"
    _description = "Resource Calendar"
    _columns = {
        'name' : fields.char("Name", size=64, required=True),
        'company_id' : fields.many2one('res.company', 'Company', required=True),
        'week_id' : fields.one2many('resource.calendar.week', 'calendar_id', 'Working Time'),
        'manager' : fields.many2one('res.users', 'Workgroup manager'),
    }
    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'resource.calendar', c)
    }

    def interval_min_get(self, cr, uid, id, dt_from, hours, resource=False):
        resource_cal_leaves = self.pool.get('resource.calendar.leaves')
        dt_leave = []
        if not id:
            return [(dt_from - mx.DateTime.RelativeDateTime(hours=int(hours)*3), dt_from)]
        resource_leave_ids = resource_cal_leaves.search(cr, uid, [('calendar_id','=',id), '|', ('resource_id','=',False), ('resource_id','=',resource)])
        res_leaves = resource_cal_leaves.read(cr, uid, resource_leave_ids, ['date_from', 'date_to'])
        for leave in res_leaves:
            dtf = mx.DateTime.strptime(leave['date_from'], '%Y-%m-%d %H:%M:%S')
            dtt = mx.DateTime.strptime(leave['date_to'], '%Y-%m-%d %H:%M:%S')
            no = dtt - dtf
            [dt_leave.append((dtf + mx.DateTime.RelativeDateTime(days=x)).strftime('%Y-%m-%d')) for x in range(int(no.days + 1))]
            dt_leave.sort()
            dt_leave.reverse()
        todo = hours
        cycle = 0
        result = []
        maxrecur = 100
        current_hour = dt_from.hour
        while (todo>0) and maxrecur:
            cr.execute("select hour_from,hour_to from resource_calendar_week where dayofweek='%s' and calendar_id=%s order by hour_from desc", (dt_from.day_of_week,id))
            for (hour_from,hour_to) in cr.fetchall():
                leave_flag  = False
                if (hour_from<current_hour) and (todo>0):
                    m = min(hour_to, current_hour)
                    if (m-hour_from)>todo:
                        hour_from = m-todo
                    dt_check = dt_from.strftime('%Y-%m-%d')
                    for leave in dt_leave:
                        if dt_check == leave:
                            dt_check = mx.DateTime.strptime(dt_check,"%Y-%m-%d") - mx.DateTime.RelativeDateTime(days=1)
                            leave_flag = True
                    if leave_flag:
                        break
                    else:
                        d1 = mx.DateTime.DateTime(dt_from.year, dt_from.month, dt_from.day, int(math.floor(hour_from)), int((hour_from%1) * 60))
                        d2 = mx.DateTime.DateTime(dt_from.year, dt_from.month, dt_from.day, int(math.floor(m)), int((m%1) * 60))
                        result.append((d1, d2))
                        current_hour = hour_from
                        todo -= (m-hour_from)
            dt_from -= mx.DateTime.RelativeDateTime(days=1)
            current_hour = 24
            maxrecur -= 1
        result.reverse()
        return result

    def interval_get(self, cr, uid, id, dt_from, hours, resource=False, byday=True):
        resource_cal_leaves = self.pool.get('resource.calendar.leaves')
        dt_leave = []
        if not id:
            return [(dt_from,dt_from + mx.DateTime.RelativeDateTime(hours=int(hours)*3))]
        resource_leave_ids = resource_cal_leaves.search(cr, uid, [('calendar_id','=',id), '|', ('resource_id','=',False), ('resource_id','=',resource)])
        res_leaves = resource_cal_leaves.read(cr, uid, resource_leave_ids, ['date_from', 'date_to'])
        for leave in res_leaves:
            dtf = mx.DateTime.strptime(leave['date_from'], '%Y-%m-%d %H:%M:%S')
            dtt = mx.DateTime.strptime(leave['date_to'], '%Y-%m-%d %H:%M:%S')
            no = dtt - dtf
            [dt_leave.append((dtf + mx.DateTime.RelativeDateTime(days=x)).strftime('%Y-%m-%d')) for x in range(int(no.days + 1))]
            dt_leave.sort()
        todo = hours
        cycle = 0
        result = []
        maxrecur = 100
        current_hour = dt_from.hour
        while (todo>0) and maxrecur:
            cr.execute("select hour_from,hour_to from resource_calendar_week where dayofweek='%s' and calendar_id=%s order by hour_from", (dt_from.day_of_week,id))
            for (hour_from,hour_to) in cr.fetchall():
                    leave_flag  = False
                    if (hour_to>current_hour) and (todo>0):
                        m = max(hour_from, current_hour)
                        if (hour_to-m)>todo:
                            hour_to = m+todo
                        dt_check = dt_from.strftime('%Y-%m-%d')
                        for leave in dt_leave:
                            if dt_check == leave:
                                dt_check = mx.DateTime.strptime(dt_check, "%Y-%m-%d") + mx.DateTime.RelativeDateTime(days=1)
                                leave_flag = True
                        if leave_flag:
                            break
                        else:
                            d1 = mx.DateTime.DateTime(dt_from.year, dt_from.month, dt_from.day, int(math.floor(m)), int((m%1) * 60))
                            d2 = mx.DateTime.DateTime(dt_from.year, dt_from.month, dt_from.day, int(math.floor(hour_to)), int((hour_to%1) * 60))
                            result.append((d1, d2))
                            current_hour = hour_to
                            todo -= (hour_to - m)
            dt_from += mx.DateTime.RelativeDateTime(days=1)
            current_hour = 0
            maxrecur -= 1
        return result

resource_calendar()

class resource_calendar_week(osv.osv):
    _name = "resource.calendar.week"
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
resource_calendar_week()

class resource_resource(osv.osv):
    _name = "resource.resource"
    _description = "Resource Detail"
    _columns = {
        'name' : fields.char("Name", size=64, required=True ),
        'code': fields.char('Code', size=16),
        'active' : fields.boolean('Active', help="If the active field is set to true, it will allow you to hide the resource record without removing it."),
        'company_id' : fields.many2one('res.company', 'Company', required=True),
        'resource_type': fields.selection([('user','Human'),('material','Material')], 'Resource Type', required=True),
        'user_id' : fields.many2one('res.users', 'User', help='Related user name for the resource to manage its access.'),
        'time_efficiency' : fields.float('Efficiency factor', size=8, required=True, help="This field depict the efficiency of the resource to complete tasks. e.g  resource put alone on a phase of 5 days with 5 tasks assigned to him, will show a load of 100% for this phase by default, but if we put a efficency of 200%, then his load will only be 50%."),
        'calendar_id' : fields.many2one("resource.calendar", "Working time", help="Define the schedule of resource"),
    }
    _defaults = {
        'resource_type' : lambda *a: 'user',
        'time_efficiency' : lambda *a: 1,
        'active' : lambda *a: True,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'resource.resource', context=c)
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

    def onchange_resource(self,cr, uid, ids, resource, context={}):
        result = {}
        if resource:
            resource_pool = self.pool.get('resource.resource')
            result['calendar_id'] = resource_pool.browse(cr, uid, resource).calendar_id.id
            return {'value': result}
        return {'value': {'calendar_id': []}}

resource_calendar_leaves()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
