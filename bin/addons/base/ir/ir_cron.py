##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
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
#
# SPEC: Execute "model.function(*eval(args))" periodically
#	date		: date to execute the job or NULL if directly
#	delete_after: delete the ir.cron entry after execution
#	interval_*  : period
#	max_repeat  : number of execution or NULL if endlessly
#
# TODO:
#	Error treatment: exception, request, ... -> send request to uid
#

from mx import DateTime
import time
import netsvc
import tools
import pooler
from osv import fields,osv

next_wait = 60

_intervalTypes = {
	'work_days': lambda interal: DateTime.RelativeDateTime(days=interval),
	'days': lambda interval: DateTime.RelativeDateTime(days=interval),
	'hours': lambda interval: DateTime.RelativeDateTime(hours=interval),
	'weeks': lambda interval: DateTime.RelativeDateTime(days=7*interval),
	'months': lambda interval: DateTime.RelativeDateTime(months=interval),
	'minutes': lambda interval: DateTime.RelativeDateTime(minutes=interval),
}

class ir_cron(osv.osv, netsvc.Agent):
	_name = "ir.cron"
	_columns = {
		'name': fields.char('Name', size=60, required=True),
		'user_id': fields.many2one('res.users', 'User', required=True),
		'active': fields.boolean('Active'),
		'interval_number': fields.integer('Interval Number'),
		'interval_type': fields.selection( [('minutes', 'Minutes'),
		    ('hours', 'Hours'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Interval Unit'),
		'numbercall': fields.integer('Number of calls', help='Number of time the function is called,\na negative number indicates that the function will always be called'),
		
		'doall' : fields.boolean('Repeat missed'),
		'nextcall' : fields.datetime('Next call date', required=True),
		'model': fields.char('Model', size=64),
		'function': fields.char('Function', size=64),
		'args': fields.text('Arguments'),
		'priority': fields.integer('Priority', help='0=Very Urgent\n10=Not urgent')
	}

	_defaults = {
		'nextcall' : lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'priority' : lambda *a: 5,
		'user_id' : lambda obj,cr,uid,context: uid,
		'interval_number' : lambda *a: 1,
		'interval_type' : lambda *a: 'months',
		'numbercall' : lambda *a: 1,
		'active' : lambda *a: 1,
		'doall' : lambda *a: 1
	}

	def _callback(self, cr, uid, model, func, args):
		args = (args or []) and eval(args)
		m=self.pool.get(model)
		if m and hasattr(m, func):
			f = getattr(m, func)
			f(cr, uid, *args)

	def _poolJobs(self, db_name, check=False):
		now = DateTime.now()
		#FIXME: multidb. Solution: a l'instanciation d'une nouvelle connection bd (ds pooler) fo que j'instancie
		# un nouveau pooljob avec comme parametre la bd
		try:
			cr = pooler.get_db(db_name).cursor()
		except:
			return False

		try:
			cr.execute('select * from ir_cron where numbercall<>0 and active and nextcall<=now() order by priority')
			for job in cr.dictfetchall():
				nextcall = DateTime.strptime(job['nextcall'], '%Y-%m-%d %H:%M:%S')
				numbercall = job['numbercall']
				
				ok = False
				while nextcall<now and numbercall:
					if numbercall > 0:
						numbercall -= 1
					if not ok or job['doall']:
						self._callback(cr, job['user_id'], job['model'], job['function'], job['args'])
					if numbercall:
						nextcall += _intervalTypes[job['interval_type']](job['interval_number'])
					ok = True
				addsql=''
				if not numbercall:
					addsql = ', active=False'
				cr.execute("update ir_cron set nextcall=%s, numbercall=%d"+addsql+" where id=%d", (nextcall.strftime('%Y-%m-%d %H:%M:%S'), numbercall, job['id']))
				cr.commit()
		finally:
			cr.close()
		#
		# Can be improved to do at the min(min(nextcalls), time()+next_wait)
		# But is this an improvement ?
		# 
		if not check:
			self.setAlarm(self._poolJobs, int(time.time())+next_wait, [db_name])
ir_cron()
