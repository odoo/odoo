##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

from osv import fields,osv
import tools

#class res_users(osv.osv):
#	_inherit = "res.users"
#	def _compute_manager_ids(self, cr, uid, ids, name, args, context):
#		res = {}
#		for id in ids:
#			cr.execute("""SELECT
#					distinct manager_id
#				from 
#					hr_department 
#				where 
#					id in (select department_id from hr_department_user_rel where user_id=%d)""", (id,))
#			res[id] = map(lambda x: x[0], cr.fetchall() or []) + [id]
#		return res
#
#	_columns = {
#		'manager_ids': fields.function(_compute_manager_ids, method=True, string='Members', type="many2many", relation="res.users"),
#	}
#res_users()

class hr_department(osv.osv):
	_name = "hr.department"
	_columns = {
		'name': fields.char('Department Name', size=64, required=True),
		'company_id': fields.many2one('res.company', 'Company', select=True, required=True),
		'parent_id': fields.many2one('hr.department', 'Parent Department', select=True),
		'child_ids': fields.one2many('hr.department', 'parent_id', 'Childs Departments'),
		'note': fields.text('Note'),
		'manager_id': fields.many2one('res.users', 'Manager', required=True),
		'member_ids': fields.many2many('res.users', 'hr_department_user_rel', 'department_id', 'user_id', 'Members'),
	}
	def _check_recursion(self, cr, uid, ids):
		level = 100
		while len(ids):
			cr.execute('select distinct parent_id from hr_department where id in ('+','.join(map(str,ids))+')')
			ids = filter(None, map(lambda x:x[0], cr.fetchall()))
			if not level:
				return False
			level -= 1
		return True
	_constraints = [
		(_check_recursion, 'Error! You can not create recursive departments.', ['parent_id'])
	]

hr_department()

