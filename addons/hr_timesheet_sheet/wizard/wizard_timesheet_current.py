##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: sign_in_out.py 2871 2006-04-25 14:08:22Z ged $
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


import wizard
import netsvc
import time
import pooler
from osv import osv

class wiz_timesheet_open(wizard.interface):
	def _open_timesheet(self, cr, uid, data, context):
		pool = pooler.get_pool(cr.dbname)
		user_ids = pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
		if not len(user_ids):
			raise wizard.except_wizard('Error !', 'No employee defined for your user !')
		ts = pool.get('hr_timesheet_sheet.sheet')
		ids = ts.search(cr, uid, [('user_id','=',uid),('state','=','draft'),('date_from','<=',time.strftime('%Y-%m-%d')), ('date_to','>=',time.strftime('%Y-%m-%d'))])
		view_type = 'form,tree'
		if len(ids) > 1:
			view_type = 'tree,form'
			domain = "[('id','in',["+','.join(map(str,ids))+"])]"
		elif len(ids)==1:
			ts.write(cr, uid, ids, {'date_current': time.strftime('%Y-%m-%d')})
			domain = "[]"
		else:
			domain = "[]"
		value = {
			'domain': domain,
			'name': 'Open timesheet',
			'view_type': 'form',
			'view_mode': view_type,
			'res_model': 'hr_timesheet_sheet.sheet',
			'view_id': False,
			'type': 'ir.actions.act_window'
		}
		if len(ids) == 1:
			value['res_id'] = ids[0]
		return value

	states = {
		'init' : {
			'actions' : [],
			'result' : {'type':'action', 'action':_open_timesheet, 'state':'end'}
		}
	}
wiz_timesheet_open('hr_timesheet_sheet.current.open')

# vim:noexpandtab:tw=0
