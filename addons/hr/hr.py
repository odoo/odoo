# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from mx import DateTime
import time
import math

from osv import fields, osv
from tools.translate import _

class hr_timesheet_group(osv.osv):
    _name = "hr.timesheet.group"
    _description = "Working Time"
    _columns = {
        'name' : fields.char("Group name", size=64, required=True),
        'timesheet_id' : fields.one2many('hr.timesheet', 'tgroup_id', 'Working Time'),
        'manager' : fields.many2one('res.users', 'Workgroup manager'),
    }
    def interval_min_get(self, cr, uid, id, dt_from, hours):
        if not id:
            return [(dt_from-DateTime.RelativeDateTime(hours=int(hours)*3), dt_from)]
        todo = hours
        cycle = 0
        result = []
        maxrecur = 100
        current_hour = dt_from.hour
        while (todo>0) and maxrecur:
            cr.execute("select hour_from,hour_to from hr_timesheet where dayofweek='%s' and tgroup_id=%s order by hour_from desc", (dt_from.day_of_week,id))
            for (hour_from,hour_to) in cr.fetchall():
                if (hour_from<current_hour) and (todo>0):
                    m = min(hour_to, current_hour)
                    if (m-hour_from)>todo:
                        hour_from = m-todo
                    d1 = DateTime.DateTime(dt_from.year,dt_from.month,dt_from.day,int(math.floor(hour_from)),int((hour_from%1) * 60))
                    d2 = DateTime.DateTime(dt_from.year,dt_from.month,dt_from.day,int(math.floor(m)),int((m%1) * 60))
                    result.append((d1, d2))
                    current_hour = hour_from
                    todo -= (m-hour_from)
            dt_from -= DateTime.RelativeDateTime(days=1)
            current_hour = 24
            maxrecur -= 1
        result.reverse()
        return result

    def interval_get(self, cr, uid, id, dt_from, hours, byday=True):
        if not id:
            return [(dt_from,dt_from+DateTime.RelativeDateTime(hours=int(hours)*3))]
        todo = hours
        cycle = 0
        result = []
        maxrecur = 100
        current_hour = dt_from.hour
        while (todo>0) and maxrecur:
            cr.execute("select hour_from,hour_to from hr_timesheet where dayofweek='%s' and tgroup_id=%s order by hour_from", (dt_from.day_of_week,id))
            for (hour_from,hour_to) in cr.fetchall():
                if (hour_to>current_hour) and (todo>0):
                    m = max(hour_from, current_hour)
                    if (hour_to-m)>todo:
                        hour_to = m+todo
                    d1 = DateTime.DateTime(dt_from.year,dt_from.month,dt_from.day,int(math.floor(m)),int((m%1) * 60))
                    d2 = DateTime.DateTime(dt_from.year,dt_from.month,dt_from.day,int(math.floor(hour_to)),int((hour_to%1) * 60))
                    result.append((d1, d2))
                    current_hour = hour_to
                    todo -= (hour_to - m)
            dt_from += DateTime.RelativeDateTime(days=1)
            current_hour = 0
            maxrecur -= 1
        return result

hr_timesheet_group()


class hr_employee_category(osv.osv):
    _name = "hr.employee.category"
    _description = "Employee Category"
    
    _columns = {
        'name' : fields.char("Category", size=64, required=True),
        'parent_id': fields.many2one('hr.employee.category', 'Parent Category', select=True),
        'child_ids': fields.one2many('hr.employee.category', 'parent_id', 'Child Categories')
    }
    
    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute('SELECT DISTINCT parent_id FROM hr_employee_category '\
                       'WHERE id IN %s', (tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True
    
    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive Categories.', ['parent_id'])
    ]
    
hr_employee_category()

class hr_employee(osv.osv):
    _name = "hr.employee"
    _description = "Employee"

    _columns = {
        'name' : fields.char("Employee", size=128, required=True),
        'active' : fields.boolean('Active'),
        'company_id': fields.many2one('res.company', 'Company'),
        'user_id' : fields.many2one('res.users', 'Related User'),

        'country_id' : fields.many2one('res.country', 'Nationality'),
        'birthday' : fields.date("Birthday"),
        'ssnid': fields.char('SSN No', size=32),
        'sinid': fields.char('SIN No', size=32),
        'otherid': fields.char('Other ID', size=32),
        'gender': fields.selection([('',''),('male','Male'),('female','Female')], 'Gender'),
        'marital': fields.selection([('maried','Maried'),('unmaried','Unmaried'),('divorced','Divorced'),('other','Other')],'Marital Status', size=32),

        'address_id': fields.many2one('res.partner.address', 'Working Address'),
        'address_home_id': fields.many2one('res.partner.address', 'Home Address'),
        'work_phone': fields.char('Work Phone', size=32),
        'work_email': fields.char('Work Email', size=128),
        'work_location': fields.char('Office Location', size=32),

        'notes': fields.text('Notes'),
        'parent_id': fields.many2one('hr.employee', 'Manager', select=True),
        'category_id' : fields.many2one('hr.employee.category', 'Category'),
        'child_ids': fields.one2many('hr.employee', 'parent_id','Subordinates'),
    }
    _defaults = {
        'active' : lambda *a: True,
    }
    
    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute('SELECT DISTINCT parent_id FROM hr_employee '\
                       'WHERE id IN %s', (tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True
    
    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive Hierarchy of Employees.', ['parent_id'])
    ]
    
hr_employee()

class hr_timesheet(osv.osv):
    _name = "hr.timesheet"
    _description = "Timesheet Line"
    _columns = {
        'name' : fields.char("Name", size=64, required=True),
        'dayofweek': fields.selection([('0','Monday'),('1','Tuesday'),('2','Wednesday'),('3','Thursday'),('4','Friday'),('5','Saturday'),('6','Sunday')], 'Day of week'),
        'date_from' : fields.date('Starting date'),
        'hour_from' : fields.float('Work from', size=8, required=True),
        'hour_to' : fields.float("Work to", size=8, required=True),
        'tgroup_id' : fields.many2one("hr.timesheet.group", "Employee's timesheet group", select=True),
    }
    _order = 'dayofweek, hour_from'
hr_timesheet()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
