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
		dep_ids = pool.get('hr.department').search(cr, uid, [('manager_id','=',uid)])
		user_ids = {}
		for dep in pool.get('hr.department').browse(cr, uid, dep_ids, context):
			for user in dep.member_ids:
				user_ids[user.id] = 1
		value = {
			'domain': "[('user_id', 'in', "+str(user_ids.keys())+")]",
			'name': 'Timesheets',
			'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'hr_timesheet_sheet.sheet',
			'view_id': False,
			'type': 'ir.actions.act_window'
		}
		return value

	states = {
		'init' : {
			'actions' : [],
			'result' : {'type':'action', 'action':_open_timesheet, 'state':'end'}
		}
	}
wiz_timesheet_open('hr_timesheet_sheet.department.open')

class wiz_timesheet_confirm_open(wizard.interface):
	def _open_timesheet(self, cr, uid, data, context):
		pool = pooler.get_pool(cr.dbname)
		dep_ids = pool.get('hr.department').search(cr, uid, [('manager_id','=',uid)])
		user_ids = {}
		for dep in pool.get('hr.department').browse(cr, uid, dep_ids, context):
			for user in dep.member_ids:
				user_ids[user.id] = 1
		value = {
			'domain': "[('user_id', 'in', "+str(user_ids.keys())+"),('state','=','draft')]",
			'name': 'Timesheets',
			'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'hr_timesheet_sheet.sheet',
			'view_id': False,
			'type': 'ir.actions.act_window'
		}
		return value

	states = {
		'init' : {
			'actions' : [],
			'result' : {'type':'action', 'action':_open_timesheet, 'state':'end'}
		}
	}
wiz_timesheet_confirm_open('hr_timesheet_sheet.department.confirm.open')


class wiz_timesheet_validate_open(wizard.interface):
	def _open_timesheet(self, cr, uid, data, context):
		pool = pooler.get_pool(cr.dbname)
		dep_ids = pool.get('hr.department').search(cr, uid, [('manager_id','=',uid)])
		user_ids = {}
		for dep in pool.get('hr.department').browse(cr, uid, dep_ids, context):
			for user in dep.member_ids:
				user_ids[user.id] = 1
		value = {
			'domain': "[('user_id', 'in', "+str(user_ids.keys())+"),('state','=','confirm')]",
			'name': 'Timesheets',
			'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'hr_timesheet_sheet.sheet',
			'view_id': False,
			'type': 'ir.actions.act_window'
		}
		return value

	states = {
		'init' : {
			'actions' : [],
			'result' : {'type':'action', 'action':_open_timesheet, 'state':'end'}
		}
	}
wiz_timesheet_validate_open('hr_timesheet_sheet.department.validate.open')


# vim:noexpandtab:tw=0
