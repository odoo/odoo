##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
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

def _action_line_create(self, cr, uid, data, context):
	tw = pooler.get_pool(cr.dbname).get('project.task.work')
	ids = tw.search(cr, uid, [('user_id','=',uid), ('date','>=',time.strftime('%Y-%m-%d 00:00:00')), ('date','<=',time.strftime('%Y-%m-%d 23:59:59'))])
	ts =  pooler.get_pool(cr.dbname).get('hr.analytic.timesheet')

	for work in tw.browse(cr, uid, ids, context):
		if work.task_id.project_id.category_id:
			unit_id = ts._getEmployeeUnit(cr, uid, context)
			product_id = ts._getEmployeeProduct(cr, uid, context)
			res = {
				'name': work.name,
				'date': time.strftime('%Y-%m-%d'),
				'unit_amount': work.hours,
				'product_uom_id': unit_id,
				'product_id': product_id,
				'amount': work.hours or 0.0,
				'account_id': work.task_id.project_id.category_id.id
			}
			res2 = ts.on_change_unit_amount(cr, uid, False, product_id, work.hours or 0.0,unit_id, context)
			if res2:
				res.update(res2['value'])
			if hasattr(ts, 'on_change_account_id'):
				res2 = ts.on_change_account_id(cr, uid, False, work.task_id.project_id.category_id.id)
				if res2:
					res.update(res2['value'])
			id = ts.create(cr, uid, res, context)

	value = {
		'domain': "[('user_id','=',%d),('date','>=','%s'), ('date','<=','%s')]" % (uid, time.strftime('%Y-%m-%d 00:00:00'), time.strftime('%Y-%m-%d 23:59:59')),
		'name': 'Create Analytic Line',
		'view_type': 'form',
		'view_mode': 'tree,form',
		'res_model': 'hr.analytic.timesheet',
		'view_id': False,
		'type': 'ir.actions.act_window'
	}
	return value

class wiz_hr_timesheet_project(wizard.interface):
	states = {
		'init': {
			'actions': [],
			'result': {'type': 'action', 'action': _action_line_create, 'state':'end'}
		}
	}
wiz_hr_timesheet_project('hr_timesheet_project.encode.hour')

