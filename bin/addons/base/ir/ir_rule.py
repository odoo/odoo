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

class ir_rule(osv.osv):
	_name = 'ir.rule'

	def _operand(self,cr,uid,context):
		def get(object, level=3, ending=[], ending_excl=[], recur=[], root_tech='', root=''):
			res= []
			fields = self.pool.get(object).fields_get(cr,uid)
			key = fields.keys()
			key.sort()
			for k in key:
				if (not ending or fields[k]['type'] in ending) and ((not ending_excl) or not (fields[k]['type'] in ending_excl)):
					res.append((root_tech+'.'+k,root+'/'+fields[k]['string']))

				if fields[k]['type'] in recur:
					res.append((root_tech+'.'+k+'.id',root+'/'+fields[k]['string']))
				if (fields[k]['type'] in recur) and (level>0):
					res.extend(get(fields[k]['relation'], level-1, ending,
								   ending_excl, recur, root_tech+'.'+k, root+'/'+fields[k]['string']))
			return res
		res = [("False", "False"),("user.id","User")]+get('res.users', level=1,ending_excl=['one2many','many2one','many2many','reference'],
														  recur=['many2one'],root_tech='user',root='User')
		return res
		
	_columns = {
		'name': fields.char('Name',size=128, required=True, select=True),
		'type': fields.selection( (('add','Additive'),('sub','Subtractive')),'Type',required=True, select=True),
		'model_id': fields.many2one('ir.model', 'Model',select=True, required=True),
		'field_id': fields.many2one('ir.model.fields', 'Field',domain= "[('model_id','=',model_id)]",select=True),
		'operator':fields.selection( (('=','='),('<>','<>'),('<=','<='),('>=','>=')),'Operator'),
		'operand':fields.selection(_operand,'Operand', size=64),
		'domain': fields.char('Domain', size=256, required=True)
	}

	_defaults={
		'type': lambda *a : 'add'
		}


	def domain_get(self, cr, uid, model_name):
		# root user above constraint
		if uid == 1:
			return '', []
		
		cr.execute("select r.id from ir_rule r join ir_model m on (r.model_id = m.id ) where m.model = %s and r.id in ( select rule_id from user_rule_rel where users_id = %d union select rule_id from group_rule_rel g join res_groups_users_rel u on (g.group_id = u.gid) where u.uid = %d )", (model_name,uid,uid))
		ids = map(lambda x:x[0], cr.fetchall())
		obj = self.pool.get(model_name)
		add = []
		add_str = []
		sub = []
		sub_str = []
		for rule in self.browse(cr, uid, ids):
			dom = eval(rule.domain, {'user': self.pool.get('res.users').browse(cr, uid, uid), 'time':time})
			d1,d2 = obj._where_calc(dom)
			if rule.type=='add':
				add_str += d1
				add +=d2
			else:
				sub_str += d1
				sub += d2
		add_str = ' or '.join(add_str)
		sub_str = ' and '.join(sub_str)

		if not (add or  sub):
			return '', []
		if add and sub:
			return '((%s) and (%s))' % (add_str, sub_str), add+sub
		if add:
			return '%s' % (add_str,), add
		if sub:
			return '%s' % (sub_str,),sub
	domain_get = tools.cache()(domain_get) 

	def onchange_rule(self, cr, uid, context, model_id, field_id, operator, operand):

		if not ( field_id and  operator and operand): return {}

		field_names= self.pool.get('ir.model.fields').read(cr,uid,[field_id], ["name"])
		if not field_names : return {}

		return {'value':{'domain': "[('%s', '%s', %s)]"%(field_names[0]['name'], operator, operand)}}

	def write(self, cr, uid, *args, **argv):
		res = super(ir_rule, self).write(cr, uid, *args, **argv)
		# Restart the cache on the company_get method
		self.domain_get()
		return res

	
ir_rule()
