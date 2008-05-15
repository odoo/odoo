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

#
# OSV: Objects Services
#

import orm
import netsvc
import pooler
import copy
import sys

import psycopg
from netsvc import Logger, LOG_ERROR
from tools.misc import UpdateableDict

module_list = []
module_class_list = {}
class_pool = {}

class except_osv(Exception):
	def __init__(self, name, value, exc_type='warning'):
		self.name = name
		self.exc_type = exc_type
		self.value = value
		self.args = (exc_type,name)

class osv_pool(netsvc.Service):

	def __init__(self):
		self.obj_pool = {}
		self.module_object_list = {}
		self.created = []
		self._sql_error = {}
		self._store_function = {}
		netsvc.Service.__init__(self, 'object_proxy', audience='')
		self.joinGroup('web-services')
		self.exportMethod(self.exportedMethods)
		self.exportMethod(self.obj_list)
		self.exportMethod(self.exec_workflow)
		self.exportMethod(self.execute)
		self.exportMethod(self.execute_cr)

	def execute_cr(self, cr, uid, obj, method, *args, **kw):
		#
		# TODO: check security level
		#
		try:
			object = pooler.get_pool(cr.dbname).get(obj)
			if not object:
				self.abortResponse(1, 'Object Error', 'warning',
				'Object %s doesn\'t exist' % str(obj))
			if (not method in getattr(object,'_protected')) and len(args) \
					and args[0] and len(object._inherits):
				types = {obj: args[0]}
				cr.execute('select inst_type,inst_id,obj_id \
						from inherit \
						where obj_type=%s \
							and  obj_id in ('+','.join(map(str,args[0]))+')', (obj,))
				for ty,id,id2 in cr.fetchall():
					if not ty in types:
						types[ty]=[]
					types[ty].append(id)
					types[obj].remove(id2)
				for t,ids in types.items():
					if len(ids):
						object_t = pooler.get_pool(cr.dbname).get(t)
						res = getattr(object_t,method)(cr, uid, ids, *args[1:], **kw)
			else:
				res = getattr(object,method)(cr, uid, *args, **kw)
			return res
		except orm.except_orm, inst:
			self.abortResponse(1, inst.name, 'warning', inst.value)
		except except_osv, inst:
			self.abortResponse(1, inst.name, inst.exc_type, inst.value)
		except psycopg.IntegrityError, inst:
			for key in self._sql_error.keys():
				if key in inst[0]:
					self.abortResponse(1, 'Constraint Error', 'warning',
							self._sql_error[key])
			self.abortResponse(1, 'Integrity Error', 'warning', inst[0])
		except Exception, e:
			import traceback
			tb_s = reduce(lambda x, y: x+y, traceback.format_exception(
				sys.exc_type, sys.exc_value, sys.exc_traceback))
			logger = Logger()
			logger.notifyChannel("web-services", LOG_ERROR,
					'Exception in call: ' + tb_s)
			raise

	def execute(self, db, uid, obj, method, *args, **kw):
		db, pool = pooler.get_db_and_pool(db)
		cr = db.cursor()
		try:
			try:
				res = pool.execute_cr(cr, uid, obj, method, *args, **kw)
				cr.commit()
			except Exception:
				cr.rollback()
				raise
		finally:
			cr.close()
		return res

	def exec_workflow_cr(self, cr, uid, obj, method, *args):
		wf_service = netsvc.LocalService("workflow")
		wf_service.trg_validate(uid, obj, args[0], method, cr)
		return True

	def exec_workflow(self, db, uid, obj, method, *args):
		cr = pooler.get_db(db).cursor()
		try:
			try:
				res = self.exec_workflow_cr(cr, uid, obj, method, *args)
				cr.commit()
			except Exception:
				cr.rollback()
				raise
		finally:
			cr.close()
		return res

	def obj_list(self):
		return self.obj_pool.keys()

	# adds a new object instance to the object pool.
	# if it already existed, the instance is replaced
	def add(self, name, obj_inst):
		if self.obj_pool.has_key(name):
			del self.obj_pool[name]
		self.obj_pool[name] = obj_inst

		module = str(obj_inst.__class__)[6:]
		module = module[:len(module)-1]
		module = module.split('.')[0][2:]
		self.module_object_list.setdefault(module, []).append(obj_inst)

	def get(self, name):
		obj = self.obj_pool.get(name, None)
# We cannot uncomment this line because it breaks initialisation since objects do not initialize
# in the correct order and the ORM doesnt support correctly when some objets do not exist yet
#		assert obj, "object %s does not exist !" % name
		return obj

	#TODO: pass a list of modules to load
	def instanciate(self, module, cr):
#		print "module list:", module_list
#		for module in module_list:
		res = []
		class_list = module_class_list.get(module, [])
#			if module not in self.module_object_list:
#		print "%s class_list:" % module, class_list
		for klass in class_list:
			res.append(klass.createInstance(self, module, cr))
		return res
#			else:
#				print "skipping module", module

#pooler.get_pool(cr.dbname) = osv_pool()

#
# See if we can use the pool var instead of the class_pool one
#
# XXX no more used
#class inheritor(type):
#	def __new__(cls, name, bases, d):
#		parent_name = d.get('_inherit', None)
#		if parent_name:
#			parent_class = class_pool.get(parent_name)
#			assert parent_class, "parent class %s does not exist !" % parent_name
#			for s in ('_columns', '_defaults', '_inherits'):
#				new_dict = copy.copy(getattr(parent_class, s))
#				new_dict.update(d.get(s, {}))
#				d[s] = new_dict
#			bases = (parent_class,)
#		res = type.__new__(cls, name, bases, d)
#		#
#		# update _inherits of others objects
#		#
#		return res



class osv(orm.orm):
	#__metaclass__ = inheritor
	def __new__(cls):
		module = str(cls)[6:]
		module = module[:len(module)-1]
		module = module.split('.')[0][2:]
		if not hasattr(cls, '_module'):
			cls._module = module
		module_class_list.setdefault(cls._module, []).append(cls)
		class_pool[cls._name] = cls
		if module not in module_list:
			module_list.append(cls._module)
		return None

	#
	# Goal: try to apply inheritancy at the instanciation level and
	#       put objects in the pool var
	#
	def createInstance(cls, pool, module, cr):
#		obj = cls()
		parent_name = hasattr(cls, '_inherit') and cls._inherit
		if parent_name:
			parent_class = pool.get(parent_name).__class__
			assert parent_class, "parent class %s does not exist !" % parent_name
			nattr = {}
			for s in ('_columns', '_defaults', '_inherits', '_constraints', '_sql_constraints'):
				new = copy.copy(getattr(pool.get(parent_name), s))
				if hasattr(new, 'update'):
					new.update(cls.__dict__.get(s, {}))
				else:
					new.extend(cls.__dict__.get(s, []))
				nattr[s] = new
			#bases = (parent_class,)
			#obj.__class__ += (parent_class,)
			#res = type.__new__(cls, name, bases, d)
			name = hasattr(cls,'_name') and cls._name or cls._inherit
			#name = str(cls)
			cls = type(name, (cls, parent_class), nattr)
		obj = object.__new__(cls)
		obj.__init__(pool, cr)
		return obj
#		return object.__new__(cls, pool)
	createInstance = classmethod(createInstance)

	def __init__(self, pool, cr):
#		print "__init__", self._name, pool
		pool.add(self._name, self)
		self.pool = pool
		orm.orm.__init__(self, cr)

#		pooler.get_pool(cr.dbname).add(self._name, self)
#		print self._name, module

class Cacheable(object):

	_cache = UpdateableDict()

	def add(self, key, value):
		self._cache[key] = value

	def invalidate(self, key):
		del self._cache[key]

	def get(self, key):
		try:
			w = self._cache[key]
			return w
		except KeyError:
			return None

	def clear(self):
		self._cache.clear()
		self._items = []

def filter_dict(d, fields):
	res = {}
	for f in fields + ['id']:
		if f in d:
			res[f] = d[f]
	return res

class cacheable_osv(osv, Cacheable):

	_relevant = ['lang']

	def __init__(self):
		super(cacheable_osv, self).__init__()

	def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
		if not fields:
			fields=[]
		if not context:
			context={}
		fields = fields or self._columns.keys()
		ctx = [context.get(x, False) for x in self._relevant]
		result, tofetch = [], []
		for id in ids:
			res = self.get(self._name, id, ctx)
			if not res:
				tofetch.append(id)
			else:
				result.append(filter_dict(res, fields))

		# gen the list of "local" (ie not inherited) fields which are classic or many2one
		nfields = filter(lambda x: x[1]._classic_write, self._columns.items())
		# gen the list of inherited fields
		inherits = map(lambda x: (x[0], x[1][2]), self._inherit_fields.items())
		# complete the field list with the inherited fields which are classic or many2one
		nfields += filter(lambda x: x[1]._classic_write, inherits)
		nfields = [x[0] for x in nfields]

		res = super(cacheable_osv, self).read(cr, user, tofetch, nfields, context, load)
		for r in res:
			self.add((self._name, r['id'], ctx), r)
			result.append(filter_dict(r, fields))

		# Appel de fonction si necessaire
		tofetch = []
		for f in fields:
			if f not in nfields:
				tofetch.append(f)
		for f in tofetch:
			fvals = self._columns[f].get(cr, self, ids, f, user, context=context)
			for r in result:
				r[f] = fvals[r['id']]

		# TODO: tri par self._order !!
		return result

	def invalidate(self, key):
		del self._cache[key[0]][key[1]]

	def write(self, cr, user, ids, values, context=None):
		if not context:
			context={}
		for id in ids:
			self.invalidate((self._name, id))
		return super(cacheable_osv, self).write(cr, user, ids, values, context)

	def unlink(self, cr, user, ids):
		self.clear()
		return super(cacheable_osv, self).unlink(cr, user, ids)

#cacheable_osv = osv

# vim:noexpandtab:

#class FakePool(object):
#	def __init__(self, module):
#		self.preferred_module = module

#	def get(self, name):
#		localpool = module_objects_dict.get(self.preferred_module, {'dict': {}})['dict']
#		if name in localpool:
#			obj = localpool[name]
#		else:
#			obj = pooler.get_pool(cr.dbname).get(name)
#		return obj

#		fake_pool = self
#		class fake_class(obj.__class__):
#			def __init__(self):
#				super(fake_class, self).__init__()
#				self.pool = fake_pool

#		return fake_class()

