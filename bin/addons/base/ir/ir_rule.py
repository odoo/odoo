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
import time
import tools


class ir_rule_group(osv.osv):
	_name = 'ir.rule.group'

	_columns = {
		'name': fields.char('Name', size=128, select=1),
		'model_id': fields.many2one('ir.model', 'Model',select=1, required=True),
		'global': fields.boolean('Global', select=1, help="Make the rule global or it needs to be put on a group or user"),
		'rules': fields.one2many('ir.rule', 'rule_group', 'Tests', help="The rule is satisfied if at least one test is True"),
		'groups': fields.many2many('res.groups', 'group_rule_group_rel', 'rule_group_id', 'group_id', 'Groups'),
		'users': fields.many2many('res.users', 'user_rule_group_rel', 'rule_group_id', 'user_id', 'Users'),
	}

	_order = 'model_id, global DESC'

	_defaults={
		'global': lambda *a: True,
	}

	def unlink(self, cr, uid, ids, context=None):
		res = super(ir_rule_group, self).unlink(cr, uid, ids, context=context)
		# Restart the cache on the domain_get method of ir.rule
		self.pool.get('ir.rule').domain_get()
		return res

	def create(self, cr, user, vals, context=None):
		res = super(ir_rule_group, self).create(cr, user, vals, context=context)
		# Restart the cache on the domain_get method of ir.rule
		self.pool.get('ir.rule').domain_get()
		return res

	def write(self, cr, uid, ids, vals, context=None):
		if not context:
			context={}
		res = super(ir_rule_group, self).write(cr, uid, ids, vals, context=context)
		# Restart the cache on the domain_get method of ir.rule
		self.pool.get('ir.rule').domain_get()
		return res

ir_rule_group()


class ir_rule(osv.osv):
	_name = 'ir.rule'
	_rec_name = 'field_id'

	def _operand(self,cr,uid,context):

		def get(object, level=3, recur=None, root_tech='', root=''):
			res = []
			if not recur:
				recur = []
			fields = self.pool.get(object).fields_get(cr,uid)
			key = fields.keys()
			key.sort()
			for k in key:

				if fields[k]['type'] in ('many2one'):
					res.append((root_tech+'.'+k+'.id',
						root+'/'+fields[k]['string']))

				elif fields[k]['type'] in ('many2many', 'one2many'):
					res.append(('\',\'.join(map(lambda x: str(x.id), '+root_tech+'.'+k+'))',
						root+'/'+fields[k]['string']))

				else:
					res.append((root_tech+'.'+k,
						root+'/'+fields[k]['string']))

				if (fields[k]['type'] in recur) and (level>0):
					res.extend(get(fields[k]['relation'], level-1,
						recur, root_tech+'.'+k, root+'/'+fields[k]['string']))

			return res

		res = [("False", "False"), ("True", "True"), ("user.id", "User")]
		res += get('res.users', level=1,
				recur=['many2one'], root_tech='user', root='User')
		return res

	def _domain_force_get(self, cr, uid, ids, field_name, arg, context={}):
		res = {}
		for rule in self.browse(cr, uid, ids, context):
			if rule.domain_force:
				res[rule.id] = rule.domain_force
			else:
				if rule.operator in ('in', 'child_of'):
					dom = eval("[('%s', '%s', [%s])]" % (rule.field_id.name, rule.operator,
						rule.operand), {'user': self.pool.get('res.users').browse(cr, 1, uid),
							'time':time})
				else:
					dom = eval("[('%s', '%s', %s)]" % (rule.field_id.name, rule.operator,
						rule.operand), {'user': self.pool.get('res.users').browse(cr, 1, uid),
							'time':time})
				res[rule.id] = dom
		return res

	_columns = {
		'field_id': fields.many2one('ir.model.fields', 'Field',domain= "[('model_id','=', parent.model_id)]", select=1, required=True),
		'operator':fields.selection((('=', '='), ('<>', '<>'), ('<=', '<='), ('>=', '>='), ('in', 'in'), ('child_of', 'child_of')), 'Operator', required=True),
		'operand':fields.selection(_operand,'Operand', size=64, required=True),
		'rule_group': fields.many2one('ir.rule.group', 'Group', select=2, required=True, ondelete="cascade"),
		'domain_force': fields.char('Force Domain', size=250),
		'domain': fields.function(_domain_force_get, method=True, string='Domain', type='char', size=250)
	}

	def onchange_all(self, cr, uid, ids, field_id, operator, operand):
		if not (field_id or operator or operand):
			return {}

	def domain_get(self, cr, uid, model_name):
		# root user above constraint
		if uid == 1:
			return '', []

		cr.execute("""SELECT r.id FROM
			ir_rule r
				JOIN (ir_rule_group g
					JOIN ir_model m ON (g.model_id = m.id))
					ON (g.id = r.rule_group)
				WHERE m.model = %s
				AND (g.id IN ( SELECT rule_group_id FROM user_rule_group_rel WHERE user_id = %d
						UNION SELECT rule_group_id FROM group_rule_group_rel g_rel
							JOIN res_groups_users_rel u_rel ON (g_rel.group_id = u_rel.gid)
							WHERE u_rel.uid = %d) OR g.global)""", (model_name, uid, uid))
		ids = map(lambda x:x[0], cr.fetchall())
		if not ids:
			return '', []
		obj = self.pool.get(model_name)
		add = []
		add_str = []
		sub = []
		sub_str = []
		clause={}
		clause_global={}
		for rule in self.browse(cr, uid, ids):
			dom = rule.domain
			if rule.rule_group['global']:
				clause_global.setdefault(rule.rule_group.id, [])
				clause_global[rule.rule_group.id].append(obj._where_calc(cr, uid, dom, active_test=False))
			else:
				clause.setdefault(rule.rule_group.id, [])
				clause[rule.rule_group.id].append(obj._where_calc(cr, uid, dom, active_test=False))

		def _query(clause, test):
			query = ''
			val = []
			for g in clause.values():
				if not g:
					continue
				if len(query):
					query += ' '+test+' '
				query += '('
				first = True
				for c in g:
					if not first:
						query += ' AND '
					first = False
					query += '('
					first2 = True
					for clause in c[0]:
						if not first2:
							query += ' AND '
						first2 = False
						query += clause
					query += ')'
					val += c[1]
				query += ')'
			return query, val

		query, val = _query(clause, 'OR')
		query_global, val_global = _query(clause_global, 'OR')
		if query_global:
			if query:
				query = '('+query+') AND '+query_global
				val.extend(val_global)
			else:
				query = query_global
				val = val_global

		return query, val
	domain_get = tools.cache()(domain_get)

	def unlink(self, cr, uid, ids, context=None):
		res = super(ir_rule, self).unlink(cr, uid, ids, context=context)
		# Restart the cache on the domain_get method of ir.rule
		self.domain_get()
		return res

	def create(self, cr, user, vals, context=None):
		res = super(ir_rule, self).create(cr, user, vals, context=context)
		# Restart the cache on the domain_get method of ir.rule
		self.domain_get()
		return res

	def write(self, cr, uid, ids, vals, context=None):
		if not context:
			context={}
		res = super(ir_rule, self).write(cr, uid, ids, vals, context=context)
		# Restart the cache on the domain_get method
		self.domain_get()
		return res

ir_rule()
