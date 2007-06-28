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
	def _get_members(self,cr, uid, context={}):
		mids = self.search(cr, uid, [('manager_id','=',uid)])
		result = {uid:1}
		for m in self.browse(cr, uid, mids, context):
			result[m.id] = 1
		return result.keys()
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


class ir_action_window(osv.osv):
	_inherit = 'ir.actions.act_window'
	def read(self, cr, uid, ids, *args, **kwargs):
		res = super(ir_action_window, self).read(cr, uid, ids, *args, **kwargs)
		for r in res:
			mystring = 'department_users_get()'
			if mystring in (r.get('domain', '[]') or ''):
				r['domain'] = r['domain'].replace(mystring, str(self.pool.get('hr.department')._get_members(cr, uid)))
		return res
ir_action_window()


