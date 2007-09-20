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

from osv import osv,fields
import pickle

class ir_values(osv.osv):
	_name = 'ir.values'
	_columns = {
		'name': fields.char('Name', size=128),
		'model': fields.char('Name', size=128),
		'value': fields.text('Value'),
		'object': fields.boolean('Is Object'),
		'key': fields.char('Name', size=128),
		'key2': fields.char('Value', size=256),
		'meta': fields.text('Meta Datas'),
		'res_id': fields.integer('Resource ID'),
		'user_id': fields.many2one('res.users', 'User', ondelete='cascade'),
		'company_id': fields.many2one('res.company', 'Company')
	}
	_defaults = {
		'key': lambda *a: 'action',
		'key2': lambda *a: 'tree_but_open',
		'company_id': lambda *a: False
	}

	def _auto_init(self, cr):
		super(ir_values, self)._auto_init(cr)
		cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'ir_values_key_model_key2_index\'')
		if not cr.fetchone():
			cr.execute('CREATE INDEX ir_values_key_model_key2_index ON ir_values (key, model, key2)')
			cr.commit()

	def set(self, cr, uid, key, key2, name, models, value, replace=True, isobject=False, meta=False, preserve_user=False, company=False):
		if type(value)==type(u''):
			value = value.encode('utf8')
		if not isobject:
			value = pickle.dumps(value)
		if meta:
			meta = pickle.dumps(meta)
		ids_res = []
		for model in models:
			if type(model)==type([]) or type(model)==type(()):
				model,res_id = model
			else:
				res_id=False
			if replace:
				ids = self.search(cr, uid, [('key','=',key),('key2','=',key2),('name','=',name),('model','=',model),('res_id','=',res_id), ('user_id','=',preserve_user and uid)])
				self.unlink(cr, uid, ids)
			vals = {
				'name': name,
				'value': value,
				'model': model,
				'object': isobject,
				'key': key,
				'key2': key2 and key2[:200],
				'meta': meta,
				'user_id': preserve_user and uid,
			}
			if company:
				cid = self.pool.get('res.users').browse(cr, uid, uid, context={}).company_id.id
				vals['company_id']=cid
			if res_id:
				vals['res_id']= res_id
			ids_res.append(self.create(cr, uid, vals))
		return ids_res

	def get(self, cr, uid, key, key2, models, meta=False, context={}, res_id_req=False, without_user=True, key2_req=True):
		result = []
		for m in models:
			if type(m)==type([]) or type(m)==type(()):
				m,res_id = m
			else:
				res_id=False
			
			where1 = ['key=%s','model=%s']
			where2 = [key,str(m)]
			where_opt = []
			if key2:
				where1.append('key2=%s')
				where2.append(key2[:200])
			else:
				dest = where1
				if not key2_req or meta:
					dest=where_opt
				dest.append('key2 is null')

			if res_id_req and (models[-1][0]==m):
				if res_id:
					where1.append('res_id=%d' % (res_id,))
				else:
					where1.append('(res_id is NULL)')
			elif res_id:
				if (models[-1][0]==m):
					where1.append('(res_id=%d or (res_id is null))' % (res_id,))
					where_opt.append('res_id=%d' % (res_id,))
				else:
					where1.append('res_id=%d' % (res_id,))

#			if not without_user:
			where_opt.append('user_id=%d' % (uid,))


			result = []
			ok = True
			while ok and len(result)==0:
				if not where_opt:
					cr.execute('select id from ir_values where ' +\
							' and '.join(where1)+' and user_id is null', where2)
				else:
					cr.execute('select id from ir_values where ' +\
							' and '.join(where1+where_opt), where2)
				result = [x[0] for x in cr.fetchall()]
				if len(where_opt):
					where_opt.pop()
				else:
					ok = False

			if result:
				break

		if not result:
			return []
		cid = self.pool.get('res.users').browse(cr, uid, uid, context={}).company_id.id
		cr.execute('select id,name,value,object,meta from ir_values where id in ('+','.join(map(str,result))+') and (company_id is null or company_id='+str(cid)+')')
		result = cr.fetchall()

		def _result_get(x):
			if x[3]:
				model,id = x[2].split(',')
				try:
					id = int(id)
				except:
					return False
				datas = self.pool.get(model).read(cr, uid, [id], False, context)
				if not len(datas):
					#ir_del(cr, uid, x[0])
					return False
				def clean(x):
					for key in ('report_sxw_content', 'report_rml_content', 'report_sxw', 'report_rml'):
						if key in x:
							del x[key]
					return x
				datas = clean(datas[0])
			else:
				datas = pickle.loads(x[2])
			if meta:
				meta2 = pickle.loads(x[4])
				return (x[0],x[1],datas,meta2)
			return (x[0],x[1],datas)
		res = filter(bool, map(lambda x: _result_get(x), list(result)))
		return res
ir_values()


