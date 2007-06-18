##############################################################################
#
# Copyright (c) 2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: hr_timesheet.py 5490 2007-01-29 16:05:51Z pinky $
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

import time
from osv import fields
from osv import osv
import netsvc

from mx import DateTime

class one2many_mod2(fields.one2many):
	def get(self, cr, obj, ids, name, user=None, offset=0, context={}, values={}):
		res = {}
		for id in ids:
			res[id] = []

		res5 = obj.read(cr, user, ids, ['date_current'], context)
		res6 = {}
		for r in res5:
			res6[r['id']] = r['date_current']

		for id in ids:
			dom = []
			if id in res6:
				dom = [('name','>=',res6[id]+' 00:00:00'),('name','<=',res6[id]+' 23:59:59')]
			ids2 = obj.pool.get(self._obj).search(cr, user, [(self._fields_id,'=',id)]+dom, limit=self._limit)
			for r in obj.pool.get(self._obj)._read_flat(cr, user, ids2, [self._fields_id], context=context, load='_classic_write'):
				res[r[self._fields_id]].append( r['id'] )
		return res


class one2many_mod(fields.one2many):
	def get(self, cr, obj, ids, name, user=None, offset=0, context={}, values={}):
		res = {}
		for id in ids:
			res[id] = []

		res5 = obj.read(cr, user, ids, ['date_current'], context)
		res6 = {}
		for r in res5:
			res6[r['id']] = r['date_current']

		for id in ids:
			dom = []
			if id in res6:
				dom = [('date','=',res6[id])]
			ids2 = obj.pool.get(self._obj).search(cr, user, [(self._fields_id,'=',id)]+dom, limit=self._limit)
			for r in obj.pool.get(self._obj)._read_flat(cr, user, ids2, [self._fields_id], context=context, load='_classic_write'):
				res[r[self._fields_id]].append( r['id'] )
		return res

class hr_timesheet_sheet(osv.osv):
	_name = "hr_timesheet_sheet.sheet"
	_table = 'hr_timesheet_sheet_sheet'
	_order = "id desc"
	def _total_attendance_day(self, cr, uid, ids, name, args, context):
		result = {}
		for day in self.browse(cr, uid, ids, context):
			result[day.id] = 0.0
			obj = self.pool.get('hr_timesheet_sheet.sheet.day')
			ids = obj.search(cr, uid, [('sheet_id','=',day.id),('name','=',day.date_current)])
			if ids:
				result[day.id] = obj.read(cr, uid, ids, ['total_attendance'])[0]['total_attendance'] or 0.0
		return result

	def _total_timesheet_day(self, cr, uid, ids, name, args, context):
		result = {}
		for day in self.browse(cr, uid, ids, context):
			result[day.id] = 0.0
			obj = self.pool.get('hr_timesheet_sheet.sheet.day')
			ids = obj.search(cr, uid, [('sheet_id','=',day.id),('name','=',day.date_current)])
			if ids:
				result[day.id] = obj.read(cr, uid, ids, ['total_timesheet'])[0]['total_timesheet'] or 0.0
		return result

	def _total_difference_day(self, cr, uid, ids, name, args, context):
		result = {}
		for day in self.browse(cr, uid, ids, context):
			result[day.id] = 0.0
			obj = self.pool.get('hr_timesheet_sheet.sheet.day')
			ids = obj.search(cr, uid, [('sheet_id','=',day.id),('name','=',day.date_current)])
			if ids:
				result[day.id] = obj.read(cr, uid, ids, ['total_difference'])[0]['total_difference'] or 0.0
		return result

	def _total_attendance(self, cr, uid, ids, name, args, context):
		cr.execute('SELECT s.id, COALESCE(SUM(d.total_attendance),0) FROM hr_timesheet_sheet_sheet s LEFT JOIN hr_timesheet_sheet_sheet_day d ON (s.id = d.sheet_id) WHERE s.id in (%s) GROUP BY s.id'%','.join(map(str, ids)))
		return dict(cr.fetchall())

	def _total_timesheet(self, cr, uid, ids, name, args, context):
		cr.execute('SELECT s.id, COALESCE(SUM(d.total_timesheet),0) FROM hr_timesheet_sheet_sheet s LEFT JOIN hr_timesheet_sheet_sheet_day d ON (s.id = d.sheet_id) WHERE s.id in (%s) GROUP BY s.id'%','.join(map(str, ids)))
		return dict(cr.fetchall())

	def _total_difference(self, cr, uid, ids, name, args, context):
		cr.execute('SELECT s.id, COALESCE(SUM(d.total_difference),0) FROM hr_timesheet_sheet_sheet s LEFT JOIN hr_timesheet_sheet_sheet_day d ON (s.id = d.sheet_id) WHERE s.id in (%s) GROUP BY s.id'%','.join(map(str, ids)))
		return dict(cr.fetchall())


	def _state_attendance(self, cr, uid, ids, name, args, context):
		result = {}
		for day in self.browse(cr, uid, ids, context):
			emp_obj = self.pool.get('hr.employee')
			emp_ids = emp_obj.search(cr, uid, [('user_id', '=', day.user_id.id)])
			if emp_ids:
				result[day.id] = emp_obj.browse(cr, uid, emp_ids[0], context).state
			else:
				result[day.id] = 'none'
		return result

	def button_confirm(self, cr, uid, ids, context):
		for sheet in self.browse(cr, uid, ids, context):
			di = sheet.user_id.company_id.timesheet_max_difference
			if (abs(sheet.total_difference) < di) or not di:
				wf_service = netsvc.LocalService("workflow")
				wf_service.trg_validate(uid, 'hr_timesheet_sheet.sheet', sheet.id, 'confirm', cr)
			else:
				raise osv.except_osv('Warning !', 'Please verify that the total difference of the sheet is lower than %.2f !' %(di,))
		return True

	def date_today(self, cr, uid, ids, context):
		for sheet in self.browse(cr, uid, ids, context):
			if DateTime.now() <= DateTime.strptime(sheet.date_from, '%Y-%m-%d'):
				self.write(cr, uid, [sheet.id], {'date_current': sheet.date_from,})
			elif DateTime.now() >= DateTime.strptime(sheet.date_to, '%Y-%m-%d'):
				self.write(cr, uid, [sheet.id], {'date_current': sheet.date_to,})
			else:
				self.write(cr, uid, [sheet.id], {'date_current': time.strftime('%Y-%m-%d')})
		return True
	def date_previous(self, cr, uid, ids, context):
		for sheet in self.browse(cr, uid, ids, context):
			if DateTime.strptime(sheet.date_current, '%Y-%m-%d') <= DateTime.strptime(sheet.date_from, '%Y-%m-%d'):
				self.write(cr, uid, [sheet.id], {'date_current': sheet.date_from,})
			else:
				self.write(cr, uid, [sheet.id], {
					'date_current': (DateTime.strptime(sheet.date_current, '%Y-%m-%d') + DateTime.RelativeDateTime(days=-1)).strftime('%Y-%m-%d'),
				})
		return True
	def date_next(self, cr, uid, ids, context):
		for sheet in self.browse(cr, uid, ids, context):
			if DateTime.strptime(sheet.date_current, '%Y-%m-%d') >= DateTime.strptime(sheet.date_to, '%Y-%m-%d'):
				self.write(cr, uid, [sheet.id], {'date_current': sheet.date_to,})
			else:
				self.write(cr, uid, [sheet.id], {
					'date_current': (DateTime.strptime(sheet.date_current, '%Y-%m-%d') + DateTime.RelativeDateTime(days=1)).strftime('%Y-%m-%d'),
				})
		return True
	def button_dummy(self, cr, uid, ids, context):
		for sheet in self.browse(cr, uid, ids, context):
			if DateTime.strptime(sheet.date_current, '%Y-%m-%d') <= DateTime.strptime(sheet.date_from, '%Y-%m-%d'):
				self.write(cr, uid, [sheet.id], {'date_current': sheet.date_from,})
			elif DateTime.strptime(sheet.date_current, '%Y-%m-%d') >= DateTime.strptime(sheet.date_to, '%Y-%m-%d'):
				self.write(cr, uid, [sheet.id], {'date_current': sheet.date_to,})
		return True
	
	def sign_in(self, cr, uid, ids, context):
		if not self.browse(cr, uid, ids, context)[0].date_current == time.strftime('%Y-%m-%d'):
			raise osv.except_osv('Error !', 'You can not sign in from an other date than today')
		emp_obj = self.pool.get('hr.employee')
		emp_id = emp_obj.search(cr, uid, [('user_id', '=', uid)])
		context['sheet_id']=ids[0]
		success = emp_obj.sign_in(cr, uid, emp_id, context=context)
		return True

	def sign_out(self, cr, uid, ids, context):
		if not self.browse(cr, uid, ids, context)[0].date_current == time.strftime('%Y-%m-%d'):
			raise osv.except_osv('Error !', 'You can not sign out from an other date than today')
		emp_obj = self.pool.get('hr.employee')
		emp_id = emp_obj.search(cr, uid, [('user_id', '=', uid)])
		context['sheet_id']=ids[0]
		success = emp_obj.sign_out(cr, uid, emp_id, context=context)
		return True

	_columns = {
		'name': fields.char('Description', size=64, select=1),
		'user_id': fields.many2one('res.users', 'User', required=True, select=1),
		'date_from': fields.date('Date from', required=True, select=1, readonly=True, states={'new':[('readonly', False)]}),
		'date_to': fields.date('Date to', required=True, select=1, readonly=True, states={'new':[('readonly', False)]}),
		'date_current': fields.date('Current date', required=True),
		'timesheet_ids' : one2many_mod('hr.analytic.timesheet', 'sheet_id', 'Timesheet lines', domain=[('date','=',time.strftime('%Y-%m-%d'))], readonly=True, states={'draft':[('readonly',False)],'new':[('readonly',False)]}),
		'attendances_ids' : one2many_mod2('hr.attendance', 'sheet_id', 'Attendances', readonly=True, states={'draft':[('readonly',False)],'new':[('readonly',False)]}),
		'state' : fields.selection([('new', 'New'),('draft','Draft'),('confirm','Confirmed'),('done','Done')], 'state', select=True, required=True, readonly=True),
		'state_attendance' : fields.function(_state_attendance, method=True, type='selection', selection=[('absent', 'Absent'), ('present', 'Present'),('none','No employee defined')], string='Current state'),
		'total_attendance_day': fields.function(_total_attendance_day, method=True, string='Total Attendance'),
		'total_timesheet_day': fields.function(_total_timesheet_day, method=True, string='Total Timesheet'),
		'total_difference_day': fields.function(_total_difference_day, method=True, string='Difference'),
		'total_attendance': fields.function(_total_attendance, method=True, string='Total Attendance'),
		'total_timesheet': fields.function(_total_timesheet, method=True, string='Total Timesheet'),
		'total_difference': fields.function(_total_difference, method=True, string='Difference'),
		'period_ids': fields.one2many('hr_timesheet_sheet.sheet.day', 'sheet_id', 'Period', readonly=True),
		'account_ids': fields.one2many('hr_timesheet_sheet.sheet.account', 'sheet_id', 'Analytic accounts', readonly=True),
	}
	def _default_date_from(self,cr, uid, context={}):
		user = self.pool.get('res.users').browse(cr, uid, uid, context)
		r = user.company_id and user.company_id.timesheet_range or 'month'
		if r=='month':
			return time.strftime('%Y-%m-01')
		elif r=='week':
			return (DateTime.now() + DateTime.RelativeDateTime(weekday=(DateTime.Monday,0))).strftime('%Y-%m-%d')
		elif r=='year':
			return time.strftime('%Y-01-01')
		return time.strftime('%Y-%m-%d')
	def _default_date_to(self,cr, uid, context={}):
		user = self.pool.get('res.users').browse(cr, uid, uid, context)
		r = user.company_id and user.company_id.timesheet_range or 'month'
		if r=='month':
			return (DateTime.now() + DateTime.RelativeDateTime(months=+1,day=1,days=-1)).strftime('%Y-%m-%d')
		elif r=='week':
			return (DateTime.now() + DateTime.RelativeDateTime(weekday=(DateTime.Sunday,0))).strftime('%Y-%m-%d')
		elif r=='year':
			return time.strftime('%Y-12-31')
		return time.strftime('%Y-%m-%d')
	_defaults = {
		'user_id': lambda self,cr,uid,c: uid,
		'date_from' : _default_date_from,
		'date_current' : lambda *a: time.strftime('%Y-%m-%d'),
		'date_to' : _default_date_to,
		'state': lambda *a: 'new',
	}

	def _sheet_date(self, cr, uid, ids):
		for sheet in self.browse(cr, uid, ids):
			cr.execute('select id from hr_timesheet_sheet_sheet where (date_from<%s and %s<date_to) and user_id=%d and id<>%d', (sheet.date_to, sheet.date_from, sheet.user_id.id, sheet.id))
			if cr.fetchall():
				return False
		return True
	_constraints = [
		(_sheet_date, 'You can not have 2 timesheets that overlaps !', ['date_from','date_to'])
	]

	def action_set_to_draft(self, cr, uid, ids, *args):
		self.write(cr, uid, ids, {'state': 'draft'})
		wf_service = netsvc.LocalService('workflow')
		for id in ids:
			wf_service.trg_create(uid, self._name, id, cr)
		return True

hr_timesheet_sheet()

def _get_current_sheet(self, cr, uid, context={}):
	ts=self.pool.get('hr_timesheet_sheet.sheet')
	ids = ts.search(cr, uid, [('user_id','=',uid),('state','=','draft'),('date_from','<=',time.strftime('%Y-%m-%d')), ('date_to','>=',time.strftime('%Y-%m-%d'))])
	if ids:
		return ids[0]
	return False


class hr_timesheet_line(osv.osv):
	_inherit = "hr.analytic.timesheet"

	def _get_default_date(self, cr, uid, context={}):
		if 'date' in context:
			return context['date']
		return time.strftime('%Y-%m-%d')

	def _sheet_date(self, cr, uid, ids):
		timesheet_lines = self.browse(cr, uid, ids)
		for l in timesheet_lines:
			if l.date[:10] < l.sheet_id.date_from:
				return False
			if l.date[:10] > l.sheet_id.date_to:
				return False
		return True

	_columns = {
		'sheet_id': fields.many2one('hr_timesheet_sheet.sheet', 'Sheet', ondelete='set null', required=True)
	}
	_defaults = {
		'sheet_id': _get_current_sheet,
		'date': _get_default_date,
	}
	_constraints = [(_sheet_date, 'Error: the timesheet line date must be in the sheet\'s dates', ['date'])]
	def create(self, cr, uid, vals, *args, **kwargs):
		if 'sheet_id' in vals:
			ts = self.pool.get('hr_timesheet_sheet.sheet').browse(cr, uid, vals['sheet_id'])
			if ts.state<>'draft':
				raise osv.except_osv('Error !', 'You can not modify an entry in a confirmed timesheet !')
		return super(hr_timesheet_line,self).create(cr, uid, vals, *args, **kwargs)
	def unlink(self, cr, uid, ids, *args, **kwargs):
		self._check(cr, uid, ids)
		return super(hr_timesheet_line,self).unlink(cr, uid, ids,*args, **kwargs)
	def write(self, cr, uid, ids, *args, **kwargs):
		self._check(cr, uid, ids)
		return super(hr_timesheet_line,self).write(cr, uid, ids,*args, **kwargs)
	def _check(self, cr, uid, ids):
		for att in self.browse(cr, uid, ids):
			if att.sheet_id and att.sheet_id.state<>'draft':
				raise osv.except_osv('Error !', 'You can not modify an entry in a confirmed timesheet !')
		return True
hr_timesheet_line()

class hr_attendance(osv.osv):
	_inherit = "hr.attendance"

	def _get_default_date(self, cr, uid, context={}):
		if 'name' in context:
			return context['name'] + time.strftime(' %H:%M:%S')
		return time.strftime('%Y-%m-%d %H:%M:%S')

	def _sheet_date(self, cr, uid, ids):
		attendances = self.browse(cr, uid, ids)
		for att in attendances:
			if att.name[:10] < att.sheet_id.date_from:
				return False
			if att.name[:10] > att.sheet_id.date_to:
				return False
		return True

	_columns = {
		'sheet_id': fields.many2one('hr_timesheet_sheet.sheet', 'Sheet', ondelete='set null', required=True)
	}
	_defaults = {
		'sheet_id': _get_current_sheet,
		'name': _get_default_date,
	}
	_constraints = [(_sheet_date, 'Error: the attendance date must be in the sheet\'s dates', ['name'])]
	def create(self, cr, uid, vals, context={}):
		if 'sheet_id' in context:
			vals['sheet_id']=context['sheet_id']
		if 'sheet_id' in vals:
			ts = self.pool.get('hr_timesheet_sheet.sheet').browse(cr, uid, vals['sheet_id'])
			if ts.state<>'draft':
				raise osv.except_osv('Error !', 'You can not modify an entry in a confirmed timesheet !')
		return super(hr_attendance,self).create(cr, uid, vals, context=context)
	def unlink(self, cr, uid, ids, *args, **kwargs):
		self._check(cr, uid, ids)
		return super(hr_attendance,self).unlink(cr, uid, ids,*args, **kwargs)
	def write(self, cr, uid, ids, vals, context={}):
		if 'sheet_id' in context:
			vals['sheet_id']=context['sheet_id']
		self._check(cr, uid, ids)
		return super(hr_attendance,self).write(cr, uid, ids, vals, context=context)
	def _check(self, cr, uid, ids):
		for att in self.browse(cr, uid, ids):
			if att.sheet_id and att.sheet_id.state<>'draft':
				raise osv.except_osv('Error !', 'You can not modify an entry in a confirmed timesheet !')
		return True
hr_attendance()

class hr_timesheet_sheet_sheet_day(osv.osv):
	_name = "hr_timesheet_sheet.sheet.day"
	_description = "Timesheets by period"
	_auto = False
	_order='name'
	_columns = {
		'name': fields.date('Date', readonly=True),
		'sheet_id': fields.many2one('hr_timesheet_sheet.sheet', 'Sheet', readonly=True, select="1"),
		'total_timesheet': fields.float('Project Timesheet', readonly=True),
		'total_attendance': fields.float('Attendance', readonly=True),
		'total_difference': fields.float('Difference', readonly=True),
	}
	def init(self, cr):
		cr.execute("""create or replace view hr_timesheet_sheet_sheet_day as
			SELECT
				MAX(id) as id,
				name,
				sheet_id,
				SUM(total_timesheet) as total_timesheet,
				CASE WHEN SUM(total_attendance) < 0
					THEN (SUM(total_attendance) +
						CASE WHEN current_date <> name
							THEN 1440
							ELSE (EXTRACT(hour FROM current_time) * 60) + EXTRACT(minute FROM current_time)
						END
						)
					ELSE SUM(total_attendance)
				END /60  as total_attendance,
				(SUM(total_attendance) - SUM(total_timesheet)) as total_difference
			FROM
				((
					select
						min(hrt.id) as id,
						l.date::date as name,
						hrt.sheet_id as sheet_id,
						sum(l.unit_amount) as total_timesheet,
						0.0 as total_attendance
					from
						hr_analytic_timesheet hrt
						left join account_analytic_line l on (l.id = hrt.line_id)
					group by l.date::date, hrt.sheet_id
				) union (
					select
						-min(a.id) as id,
						a.name::date as name,
						a.sheet_id as sheet_id,
						0.0 as total_timesheet,
						SUM(((EXTRACT(hour FROM a.name) * 60) + EXTRACT(minute FROM a.name)) * (CASE WHEN a.action = 'sign_in' THEN -1 ELSE 1 END)) as total_attendance
					from
						hr_attendance a
					group by a.name::date, a.sheet_id
				)) AS foo
				GROUP BY name, sheet_id""")
hr_timesheet_sheet_sheet_day()


class hr_timesheet_sheet_sheet_account(osv.osv):
	_name = "hr_timesheet_sheet.sheet.account"
	_description = "Timesheets by period"
	_auto = False
	_order='name'
	_columns = {
		'name': fields.many2one('account.analytic.account', 'Analytic Account', readonly=True),
		'sheet_id': fields.many2one('hr_timesheet_sheet.sheet', 'Sheet', readonly=True),
		'total': fields.float('Total Time', digits=(16,2), readonly=True),
		'invoice_rate': fields.many2one('hr_timesheet_invoice.factor', 'Invoice rate', readonly=True),
	}
	def init(self, cr):
		cr.execute("""create or replace view hr_timesheet_sheet_sheet_account as (
			select
				min(hrt.id) as id,
				l.account_id as name,
				hrt.sheet_id as sheet_id,
				sum(l.unit_amount) as total,
				l.to_invoice as invoice_rate
			from
				hr_analytic_timesheet hrt
				left join account_analytic_line l on (l.id = hrt.line_id)
			group by l.account_id, hrt.sheet_id, l.to_invoice
		)""")
hr_timesheet_sheet_sheet_account()

class res_company(osv.osv):
	_inherit = 'res.company'
	_columns = {
		'timesheet_range': fields.selection([('day','Day'),('week','Week'),('month','Month'),('year','Year')], 'Timeshet range', required=True),
		'timesheet_max_difference': fields.float('Timesheet allowed difference', help="Allowed difference between the sign in/out and the timesheet computation for one sheet. Set this to 0 if you do not want any control."),
	}
	_defaults = {
		'timesheet_range': lambda *args: 'month',
		'timesheet_max_difference': lambda *args: 0.0
	}
res_company()
