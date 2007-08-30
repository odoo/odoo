##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from mx import DateTime
import time

from osv import fields, osv

class hr_timesheet_group(osv.osv):
	_name = "hr.timesheet.group"
	_description = "Timesheet"
	_columns = {
		'name' : fields.char("Group name", size=64, required=True),
		'timesheet_id' : fields.one2many('hr.timesheet', 'tgroup_id', 'Timesheet'),
		'manager' : fields.many2one('res.users', 'Workgroup manager'),
	}
	#
	# TODO: improve; very slow !
	#       bug if transition to another period
	#
	def interval_get(self, cr, uid, id, dt_from, hours, byday=True):
		if not id:
			return [(dt_from,dt_from+DateTime.RelativeDateTime(hours=int(hours)*3))]
		todo = hours
		cycle = 0
		result = []
		while todo>0:
			cr.execute('select hour_from,hour_to from hr_timesheet where dayofweek=%d and tgroup_id=%d order by hour_from', (dt_from.day_of_week,id))
			for (hour_from,hour_to) in cr.fetchall():
				h1,m1 = map(int,hour_from.split(':'))
				h2,m2 = map(int,hour_to.split(':'))
				d1 = DateTime.DateTime(dt_from.year,dt_from.month,dt_from.day,h1,m1)
				d2 = DateTime.DateTime(dt_from.year,dt_from.month,dt_from.day,h2,m2)
				if dt_from<d2:
					date1 = max(dt_from,d1)
					if date1+DateTime.RelativeDateTime(hours=todo)<=d2:
						result.append((date1, date1+DateTime.RelativeDateTime(hours=todo)))
						todo = 0
					else:
						todo -= (d2-date1).hours
						result.append((date1, d2))
			dt_from = DateTime.DateTime(dt_from.year,dt_from.month,dt_from.day)+DateTime.RelativeDateTime(days=1)
			cycle+=1
			if cycle>7 and todo==hours:
				return [(dt_from,dt_from+DateTime.RelativeDateTime(hours=hours*3))]
		if byday:
			i = 1
			while i<len(result):
				if (result[i][0]-result[i-1][1]).days<1:
					result[i-1]=(result[i-1][0],result[i][1])
					del result[i]
				else:
					i+=1
		return result
hr_timesheet_group()


class hr_employee_category(osv.osv):
	_name = "hr.employee.category"
	_description = "Employee Category"
	_columns = {
		'name' : fields.char("Category", size=64, required=True),
		'parent_id': fields.many2one('hr.employee.category', 'Parent category', select=True),
		'child_ids': fields.one2many('hr.employee.category', 'parent_id', 'Childs Categories')
	}
hr_employee_category()

class hr_employee(osv.osv):
	_name = "hr.employee"
	_description = "Employee"

	def _state(self, cr, uid, ids, name, args, context={}):
		result = {}
		for id in ids:
			result[id] = 'absent'
		cr.execute('SELECT hr_attendance.action, hr_attendance.employee_id \
				FROM ( \
					SELECT MAX(name) AS name, employee_id \
					FROM hr_attendance \
					WHERE action in (\'sign_in\', \'sign_out\') \
					GROUP BY employee_id \
				) AS foo \
				LEFT JOIN hr_attendance \
					ON (hr_attendance.employee_id = foo.employee_id \
						AND hr_attendance.name = foo.name) \
				WHERE hr_attendance.employee_id \
					in (' + ','.join([str(x) for x in ids]) + ')')
		for res in cr.fetchall():
			result[res[1]] = res[0] == 'sign_in' and 'present' or 'absent'
		return result

	_columns = {
		'name' : fields.char("Employee", size=128, required=True),
		'active' : fields.boolean('Active'),
		'company_id': fields.many2one('res.company', 'Company'),
		'address_id': fields.many2one('res.partner.address', 'Contact address'),
		'state': fields.function(_state, method=True, type='selection', selection=[('absent', 'Absent'), ('present', 'Present')], string='Attendance'),
		'started' : fields.date("Started on"),
		'notes': fields.text('Notes'),
		'attendances' : fields.one2many('hr.attendance', 'employee_id', "Employee's attendances"),
		'holidays' : fields.one2many('hr.holidays', 'employee_id', "Employee's holidays"),
		'workgroups' : fields.many2many('hr.timesheet.group', 'hr_timesheet_employee_rel', 'emp_id', 'tgroup_id', "Employee's work team"),
		'user_id' : fields.many2one('res.users', 'Tiny ERP User'),
		'category_id' : fields.many2one('hr.employee.category', 'Category'),
		'regime' : fields.float('Workhours by week'),
		'holiday_max' : fields.integer("Number of holidays"),
		'parent_id': fields.many2one('hr.employee', 'Boss', select=True),
		'child_ids': fields.one2many('hr.employee', 'parent_id','Subordinates'),
	}
	_defaults = {
		'active' : lambda *a: True,
		'state' : lambda *a: 'absent',
	}
	def sign_change(self, cr, uid, ids, context={}, dt=False):
		for emp in self.browse(cr, uid, ids):
			if not self._action_check(cr, uid, emp.id, dt, context):
				raise osv.except_osv('Warning', 'You tried to sign with a date anterior to another event !\nTry to contact the administrator to correct attendances.')
			res = {'action':'action', 'employee_id':emp.id}
			if dt:
				res['name'] = dt
			att_id = self.pool.get('hr.attendance').create(cr, uid, res, context=context)
		return True

	def sign_out(self, cr, uid, ids, context={}, dt=False, *args):
		id = False
		for emp in self.browse(cr, uid, ids):
			if not self._action_check(cr, uid, emp.id, dt, context):
				raise osv.except_osv('Warning', 'You tried to sign out with a date anterior to another event !\nTry to contact the administrator to correct attendances.')
			res = {'action':'sign_out', 'employee_id':emp.id}
			if dt:
				res['name'] = dt
			att_id = self.pool.get('hr.attendance').create(cr, uid, res, context=context)
			id = att_id
		return id

	def _action_check(self, cr, uid, emp_id, dt=False,context={}):
		cr.execute('select max(name) from hr_attendance where employee_id=%d', (emp_id,))
		res = cr.fetchone()
		return not (res and (res[0]>=(dt or time.strftime('%Y-%m-%d %H:%M:%S'))))

	def sign_in(self, cr, uid, ids, context={}, dt=False, *args):
		id = False
		for emp in self.browse(cr, uid, ids):
			if not self._action_check(cr, uid, emp.id, dt, context):
				raise osv.except_osv('Warning', 'You tried to sign in with a date anterior to another event !\nTry to contact the administrator to correct attendances.')
			res = {'action':'sign_in', 'employee_id':emp.id}
			if dt:
				res['name'] = dt
			id = self.pool.get('hr.attendance').create(cr, uid, res, context=context)
		return id

hr_employee()

class hr_timesheet(osv.osv):
	_name = "hr.timesheet"
	_description = "Timesheet Line"
	_columns = {
		'name' : fields.char("Name", size=64, required=True),
		'dayofweek': fields.selection([('0','Monday'),('1','Tuesday'),('2','Wednesday'),('3','Thursday'),('4','Friday'),('5','Saturday'),('6','Sunday')], 'Day of week'),
		'date_from' : fields.date('Starting date'),
		'hour_from' : fields.char('Work from', size=8, required=True),
		'hour_to' : fields.char("Work to", size=8, required=True),
		'tgroup_id' : fields.many2one("hr.timesheet.group", "Employee's timesheet group", select=True),
	}
	_order = 'dayofweek, hour_from'
hr_timesheet()

class hr_action_reason(osv.osv):
	_name = "hr.action.reason"
	_description = "Action reason"
	_columns = {
		'name' : fields.char('Reason', size=64, required=True),
		'action_type' : fields.selection([('sign_in', 'Sign in'), ('sign_out', 'Sign out')], "Action's type"),
	}
	_defaults = {
		'action_type' : lambda *a: 'sign_in',
	}
hr_action_reason()

def _employee_get(obj,cr,uid,context={}):
	ids = obj.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)])
	if ids:
		return ids[0]
	return False

class hr_attendance(osv.osv):
	_name = "hr.attendance"
	_description = "Attendance"
	_columns = {
		'name' : fields.datetime('Date', required=True),
		'action' : fields.selection([('sign_in', 'Sign In'), ('sign_out', 'Sign Out'),('action','Action')], 'Action', required=True),
		'action_desc' : fields.many2one("hr.action.reason", "Action reason", domain="[('action_type', '=', action)]"),
		'employee_id' : fields.many2one('hr.employee', 'Employee', required=True, select=True),
	}
	_defaults = {
		'name' : lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'employee_id' : _employee_get,
	}
	
	def _altern_si_so(self, cr, uid, ids):
		for id in ids:
			sql = '''
			select action, name
			from hr_attendance as att
			where employee_id = (select employee_id from hr_attendance where id=%s)
			and action in ('sign_in','sign_out')
			and name <= (select name from hr_attendance where id=%s)
			order by name desc
			limit 2
			''' % (id, id)
			cr.execute(sql)
			atts = cr.fetchall()
			if not ((len(atts)==1 and atts[0][0] == 'sign_in') or (atts[0][0] != atts[1][0] and atts[0][1] != atts[1][1])):
				return False
		return True
	
	_constraints = [(_altern_si_so, 'Error: Sign in (resp. Sign out) must follow Sign out (resp. Sign in)', ['action'])]
	_order = 'name desc'
hr_attendance()

class hr_holidays_status(osv.osv):
	_name = "hr.holidays.status"
	_description = "Holidays Status"
	_columns = {
		'name' : fields.char('Holiday Status', size=64, required=True, translate=True),
	}
hr_holidays_status()

class hr_holidays(osv.osv):
	_name = "hr.holidays"
	_description = "Holidays"
	_columns = {
		'name' : fields.char('Description', required=True, size=64),
		'date_from' : fields.datetime('Vacation start day', required=True),
		'date_to' : fields.datetime('Vacation end day'),
		'holiday_status' : fields.many2one("hr.holidays.status", "Holiday's Status"),
		'employee_id' : fields.many2one('hr.employee', 'Employee', select=True),
	}
	_defaults = {
		'employee_id' : _employee_get
	}
	_order = 'date_from desc'
hr_holidays()

# vim:tw=0:noexpandtab
