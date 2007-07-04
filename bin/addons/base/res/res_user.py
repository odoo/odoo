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

class groups(osv.osv):
	_name = "res.groups"
	_columns = {
		'name': fields.char('Group Name', size=64, required=True),
		'rule_groups': fields.many2many('ir.rule.group', 'group_rule_group_rel', 'group_id', 'rule_group_id', 'Rules', domain="[('global', '<>', True)]"),
	}
	def write(self, cr, uid, *args, **argv):
		res = super(groups, self).write(cr, uid, *args, **argv)
		# Restart the cache on the company_get method
		self.pool.get('ir.rule').domain_get()
		return res
groups()


class roles(osv.osv):
	_name = "res.roles"
	_columns = {
		'name': fields.char('Role Name', size=64, required=True),
		'parent_id': fields.many2one('res.roles', 'Parent', select=True),
		'child_id': fields.one2many('res.roles', 'parent_id', 'Childs')
	}
	_defaults = {
	}
	def check(self, cr, uid, ids, role_id):
		if role_id in ids:
			return True
		cr.execute('select parent_id from res_roles where id=%d', (role_id,))
		roles = cr.fetchone()[0]
		if roles:
			return self.check(cr, uid, ids, roles)
		return False
roles()

class lang(osv.osv):
	_name = "res.lang"
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'code': fields.char('Code', size=5, required=True),
		'translatable': fields.boolean('Translatable'),
		'active': fields.boolean('Active'),
		'direction': fields.selection([('ltr', 'Left-to-right'), ('rtl', 'Right-to-left')], 'Direction',resuired=True),
	}
	_defaults = {
		'active': lambda *a: 1,
		'translatable': lambda *a: 0,
		'direction': lambda *a: 'ltr',
	}
lang()

class users(osv.osv):
	_name = "res.users"
	_log_access = False
	_columns = {
		'name': fields.char('Name', size=64, required=True, select=True),
		'login': fields.char('Login', size=64, required=True),
		'password': fields.char('Password', size=64, invisible=True),
		'signature': fields.text('Signature', size=64),
		'address_id': fields.many2one('res.partner.address', 'Address'),
		'active': fields.boolean('Active'),
		'action_id': fields.many2one('ir.actions.actions', 'Home Action'),
		'menu_id': fields.many2one('ir.actions.actions', 'Menu Action'),
		'groups_id': fields.many2many('res.groups', 'res_groups_users_rel', 'uid', 'gid', 'Groups'),
		'roles_id': fields.many2many('res.roles', 'res_roles_users_rel', 'uid', 'rid', 'Roles'),
		'company_id': fields.many2one('res.company', 'Company'),
		'rule_groups': fields.many2many('ir.rule.group', 'user_rule_group_rel', 'user_id', 'rule_group_id', 'Rules', domain="[('global', '<>', True)]"),
	}
	_sql_constraints = [
		('login_key', 'UNIQUE (login)', 'You can not have two users with the same login !')
	]
	_defaults = {
		'password' : lambda obj,cr,uid,context={} : '',
		'active' : lambda obj,cr,uid,context={} : True,
	}
	def company_get(self, cr, uid, uid2):
		company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
		return company_id
	company_get = tools.cache()(company_get)

	def write(self, cr, uid, *args, **argv):
		res = super(users, self).write(cr, uid, *args, **argv)
		self.company_get()
		# Restart the cache on the company_get method
		self.pool.get('ir.rule').domain_get()
		return res

	def unlink(self, cr, uid, ids):
		if 1 in ids:
			raise osv.except_osv('Can not remove root user !', 'You can not remove the root user as it is used internally for resources created by Tiny ERP (updates, module installation, ...)')
		return super(users, self).unlink(cr, uid, ids)
		
	def name_search(self, cr, user, name, args=[], operator='ilike', context={}):
		ids = self.search(cr, user, [('login','=',name)]+ args)
		if not ids:
			ids = self.search(cr, user, [('name',operator,name)]+ args)
		return self.name_get(cr, user, ids)
		
	def copy(self, cr, uid, id, default=None, context={}):
		login = self.read(cr, uid, [id], ['login'])[0]['login']
		default.update({'login': login+' (copy)'})
		return super(users, self).copy(cr, uid, id, default, context)


users()

