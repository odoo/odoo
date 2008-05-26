# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: orm.py 1008 2005-07-25 14:03:55Z pinky $
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
# Object relationnal mapping to postgresql module
#    . Hierarchical structure
#    . Constraints consistency, validations
#    . Object meta Data depends on its status
#    . Optimised processing by complex query (multiple actions at once)
#    . Default fields value
#    . Permissions optimisation
#    . Persistant object: DB postgresql
#    . Datas conversions
#    . Multi-level caching system
#    . 2 different inheritancies
#    . Fields:
#         - classicals (varchar, integer, boolean, ...)
#         - relations (one2many, many2one, many2many)
#         - functions
#
#

from xml import dom, xpath
from xml.parsers import expat
import string
import pooler
import psycopg
import netsvc
import re

import fields
import ir
import tools

prof = 0
ID_MAX = 1000

regex_order = re.compile('^([a-zA-Z0-9_]+( desc)?,?)+$')

def intersect(la, lb):
	return filter(lambda x: x in lb, la)


class except_orm(Exception):
	def __init__(self, name, value):
		self.name = name
		self.value = value
		self.args = (name, value)

#class find_fields(object):
#	def _start_el(self,name, attrs):
#		if name == 'field' and attrs.get('name', False):
#			self.datas[str(attrs['name'])] = attrs.get('preload','')
#	def __init__(self):
#		self.datas = {}
#	def parse(self, datas):
#		p = expat.ParserCreate()
#		p.StartElementHandler = self._start_el
#		p.Parse(datas, 1)
#		return self.datas

#
# TODO: trigger pour chaque action
#
# Readonly python database object browser
class browse_null(object):

	def __init__(self):
		self.id=False

	def __getitem__(self, name):
		return False

	def __int__(self):
		return False

	def __str__(self):
		return ''

	def __nonzero__(self):
		return False

#
# TODO: execute an object method on browse_record_list
#
class browse_record_list(list):

	def __init__(self, lst, context=None):
		if not context:
			context = {}
		super(browse_record_list, self).__init__(lst)
		self.context = context


class browse_record(object):
	def __init__(self, cr, uid, id, table, cache, context=None, list_class = None):
		'''
		table : the object (inherited from orm)
		context : a dictionnary with an optionnal context
		'''
		if not context:
			context = {}
		assert id, 'Wrong ID for the browse record, got '+str(id)+ ', expected an integer.'
		self._list_class = list_class or browse_record_list
		self._cr = cr
		self._uid = uid
		self._id = id
		self._table = table
		self._table_name = self._table._name
		self._context = context

		cache.setdefault(table._name, {})
		self._data = cache[table._name]
		if not id in self._data:
			self._data[id] = {'id':id}
		self._cache = cache

	def __getitem__(self, name):
		if name == 'id':
			return self._id
		if not self._data[self._id].has_key(name):
			# build the list of fields we will fetch

			# fetch the definition of the field which was asked for
			if name in self._table._columns:
				col = self._table._columns[name]
			elif name in self._table._inherit_fields:
				col = self._table._inherit_fields[name][2]
			elif hasattr(self._table, name):
				return getattr(self._table, name)
			else:
				logger = netsvc.Logger()
				logger.notifyChannel('orm', netsvc.LOG_ERROR, "Programming error: field '%s' does not exist in object '%s' !" % (name, self._table._name))
				return False

			# if the field is a classic one or a many2one, we'll fetch all classic and many2one fields
			if col._classic_write:
				# gen the list of "local" (ie not inherited) fields which are classic or many2one
				ffields = filter(lambda x: x[1]._classic_write, self._table._columns.items())
				# gen the list of inherited fields
				inherits = map(lambda x: (x[0], x[1][2]), self._table._inherit_fields.items())
				# complete the field list with the inherited fields which are classic or many2one
				ffields += filter(lambda x: x[1]._classic_write, inherits)
			# otherwise we fetch only that field
			else:
				ffields = [(name,col)]
			ids = filter(lambda id: not self._data[id].has_key(name), self._data.keys())
			# read the data
			datas = self._table.read(self._cr, self._uid, ids, map(lambda x: x[0], ffields), context=self._context, load="_classic_write")

			# create browse records for 'remote' objects
			for data in datas:
				for n,f in ffields:
					if f._type in ('many2one', 'one2one'):
						if data[n]:
							obj = self._table.pool.get(f._obj)
							compids=False
							if not f._classic_write:
								ids2 = data[n][0]
							else:
								ids2 = data[n]
							data[n] = browse_record(self._cr, self._uid, ids2, obj, self._cache, context=self._context, list_class=self._list_class)
						else:
							data[n] = browse_null()
					elif f._type in ('one2many', 'many2many') and len(data[n]):
						data[n] = self._list_class([browse_record(self._cr,self._uid,id,self._table.pool.get(f._obj),self._cache, context=self._context, list_class=self._list_class) for id in data[n]], self._context)
				self._data[data['id']].update(data)
		return self._data[self._id][name]

	def __getattr__(self, name):
#		raise an AttributeError exception.
		return self[name]

	def __contains__(self, name):
		return (name in self._table._columns) or (name in self._table._inherit_fields) or hasattr(self._table, name)

	def __hasattr__(self, name):
		return name in self

	def __int__(self):
		return self._id

	def __str__(self):
		return "browse_record(%s, %d)" % (self._table_name, self._id)

	def __eq__(self, other):
		return (self._table_name, self._id) == (other._table_name, other._id)

	def __ne__(self, other):
		return (self._table_name, self._id) != (other._table_name, other._id)

	# we need to define __unicode__ even though we've already defined __str__
	# because we have overridden __getattr__
	def __unicode__(self):
		return unicode(str(self))

	def __hash__(self):
		return hash((self._table_name, self._id))

	__repr__ = __str__


def get_pg_type(f):
	'''
	returns a tuple
	(type returned by postgres when the column was created, type expression to create the column)
	'''

	type_dict = {
			fields.boolean:'bool',
			fields.integer:'int4',
			fields.text:'text',
			fields.date:'date',
			fields.time:'time',
			fields.datetime:'timestamp',
			fields.binary:'bytea',
			fields.many2one:'int4',
			}
	if type_dict.has_key(type(f)):
		f_type = (type_dict[type(f)], type_dict[type(f)])
	elif isinstance(f, fields.float):
		if f.digits:
			f_type = ('numeric', 'NUMERIC(%d,%d)' % (f.digits[0],f.digits[1]))
		else:
			f_type = ('float8', 'DOUBLE PRECISION')
	elif isinstance(f, (fields.char, fields.reference)):
		f_type = ('varchar', 'VARCHAR(%d)' % (f.size,))
	elif isinstance(f, fields.selection):
		if isinstance(f.selection, list) and isinstance(f.selection[0][0], (str, unicode)):
			f_size = reduce(lambda x,y: max(x,len(y[0])), f.selection, f.size or 16)
		elif isinstance(f.selection, list) and isinstance(f.selection[0][0], int):
			f_size = -1
		else:
			f_size = (hasattr(f,'size') and f.size) or 16

		if f_size == -1:
			f_type = ('int4', 'INTEGER')
		else:
			f_type = ('varchar', 'VARCHAR(%d)' % f_size)
	elif isinstance(f, fields.function) and type_dict.has_key(eval('fields.'+(f._type))):
		t=eval('fields.'+(f._type))
		f_type = (type_dict[t], type_dict[t])
	elif isinstance(f, fields.function) and f._type == 'float':
		f_type = ('float8', 'DOUBLE PRECISION')
	elif isinstance(f, fields.function) and f._type == 'selection':
		f_type = ('text', 'text')
	else:
		logger = netsvc.Logger()
		logger.notifyChannel("init", netsvc.LOG_WARNING, '%s type not supported!' % (type(f)))
		f_type = None
	return f_type


class orm(object):
	_columns = {}
	_sql_constraints = []
	_constraints = []
	_defaults = {}
	_log_access = True
	_table = None
	_name = None
	_rec_name = 'name'
	_parent_name = 'parent_id'
	_date_name = 'date'
	_order = 'id'
	_inherits = {}
	_sequence = None
	_description = None
	_protected = ['read','write','create','default_get','perm_read','perm_write','unlink','fields_get','fields_view_get','search','name_get','distinct_field_get','name_search','copy','import_data','search_count']
	def _field_create(self, cr):
		cr.execute("SELECT id FROM ir_model WHERE model='%s'" % self._name)
		if not cr.rowcount:
			# reference model in order to have a description of its fonctionnality in custom_report
			cr.execute("INSERT INTO ir_model (model, name, info) VALUES (%s, %s, %s)", (self._name, self._description, self.__doc__))
		cr.commit()
		for k in self._columns:
			f = self._columns[k]
			cr.execute("select id, relate from ir_model_fields where model=%s and name=%s", (self._name,k))
			if not cr.rowcount:
				cr.execute("select id from ir_model where model='%s'" % self._name)
				model_id = cr.fetchone()[0]
				cr.execute("INSERT INTO ir_model_fields (model_id, model, name, field_description, ttype, relate,relation,group_name,view_load,state,select_level) VALUES (%d,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (model_id, self._name, k, f.string.replace("'", " "), f._type, (f.relate and 'True') or 'False', f._obj or 'NULL', f.group_name or '', (f.view_load and 'True') or 'False', 'base', str(f.select or 0)))
			else:
				id, relate = cr.fetchone()
				if relate != f.relate:
					cr.execute("UPDATE ir_model_fields SET relate=%s WHERE id=%d", ((f.relate and 'True') or 'False', id))
		cr.commit()

	def _auto_init(self, cr):
		logger = netsvc.Logger()
		create = False
		self._field_create(cr)
		if not hasattr(self, "_auto") or self._auto:
			cr.execute("SELECT relname FROM pg_class WHERE relkind in ('r','v') AND relname='%s'" % self._table)
			if not cr.rowcount:
				cr.execute("CREATE TABLE \"%s\" (id SERIAL NOT NULL, perm_id INTEGER, PRIMARY KEY(id)) WITH OIDS" % self._table)
				create = True
			cr.commit()
			if self._log_access:
				logs = {
					'create_uid': 'INTEGER REFERENCES res_users ON DELETE SET NULL',
					'create_date': 'TIMESTAMP',
					'write_uid': 'INTEGER REFERENCES res_users ON DELETE SET NULL',
					'write_date': 'TIMESTAMP'
				}
				for k in logs:
					cr.execute(
						"""
						SELECT c.relname
						FROM pg_class c, pg_attribute a
						WHERE c.relname='%s' AND a.attname='%s' AND c.oid=a.attrelid
						""" % (self._table, k))
					if not cr.rowcount:
						cr.execute("ALTER TABLE \"%s\" ADD COLUMN \"%s\" %s" %
							(self._table, k, logs[k]))
						cr.commit()

			# iterate on the database columns to drop the NOT NULL constraints
			# of fields which were required but have been removed
			cr.execute(
				"SELECT a.attname, a.attnotnull "\
				"FROM pg_class c, pg_attribute a "\
				"WHERE c.oid=a.attrelid AND c.relname='%s'" % self._table)
			db_columns = cr.dictfetchall()
			for column in db_columns:
				if column['attname'] not in ('id', 'oid', 'tableoid', 'ctid', 'xmin', 'xmax', 'cmin', 'cmax'):
					if column['attnotnull'] and column['attname'] not in self._columns:
						cr.execute("ALTER TABLE \"%s\" ALTER COLUMN \"%s\" DROP NOT NULL" % (self._table, column['attname']))

			# iterate on the "object columns"
			for k in self._columns:
				if k in ('id','perm_id','write_uid','write_date','create_uid','create_date'):
					continue
					#raise 'Can not define a column %s. Reserved keyword !' % (k,)
				f = self._columns[k]

				if isinstance(f, fields.one2many):
					cr.execute("SELECT relname FROM pg_class WHERE relkind='r' AND relname=%s", (f._obj,))
					if cr.fetchone():
						cr.execute("SELECT count(*) as c FROM pg_class c,pg_attribute a WHERE c.relname=%s AND a.attname=%s AND c.oid=a.attrelid", (f._obj,f._fields_id))
						res = cr.fetchone()[0]
						if not res:
							cr.execute("ALTER TABLE \"%s\" ADD FOREIGN KEY (%s) REFERENCES \"%s\" ON DELETE SET NULL" % (self._obj, f._fields_id, f._table))
				elif isinstance(f, fields.many2many):
					cr.execute("SELECT relname FROM pg_class WHERE relkind in ('r','v') AND relname=%s", (f._rel,))
					if not cr.dictfetchall():
						#FIXME: Remove this try/except
						try:
							ref = self.pool.get(f._obj)._table
						except AttributeError:
							ref = f._obj.replace('.','_')
						cr.execute("CREATE TABLE \"%s\" (\"%s\" INTEGER NOT NULL REFERENCES \"%s\" ON DELETE CASCADE, \"%s\" INTEGER NOT NULL REFERENCES \"%s\" ON DELETE CASCADE) WITH OIDS"%(f._rel,f._id1,self._table,f._id2,ref))
						cr.execute("CREATE INDEX \"%s_%s_index\" ON \"%s\" (\"%s\")" % (f._rel,f._id1,f._rel,f._id1))
						cr.execute("CREATE INDEX \"%s_%s_index\" ON \"%s\" (\"%s\")" % (f._rel,f._id2,f._rel,f._id2))
						cr.commit()
				else:
					cr.execute("SELECT c.relname,a.attname,a.attlen,a.atttypmod,a.attnotnull,a.atthasdef,t.typname,CASE WHEN a.attlen=-1 THEN a.atttypmod-4 ELSE a.attlen END as size FROM pg_class c,pg_attribute a,pg_type t WHERE c.relname=%s AND a.attname=%s AND c.oid=a.attrelid AND a.atttypid=t.oid", (self._table, k))
					res = cr.dictfetchall()
					if not res:
						if not isinstance(f,fields.function) or f.store:

							# add the missing field
							cr.execute("ALTER TABLE \"%s\" ADD COLUMN \"%s\" %s" % (self._table, k, get_pg_type(f)[1]))

							# initialize it
							if not create and k in self._defaults:
								default = self._defaults[k](self, cr, 1, {})
								if not default:
									cr.execute("UPDATE \"%s\" SET \"%s\"=NULL" % (self._table, k))
								else:
									cr.execute("UPDATE \"%s\" SET \"%s\"='%s'" % (self._table, k, default))
							if isinstance(f,fields.function):
								cr.execute('select id from '+self._table)
								ids_lst = map(lambda x: x[0], cr.fetchall())
								while ids_lst:
									iids = ids_lst[:40]
									ids_lst = ids_lst[40:]
									res = f.get(cr, self, iids, k, 1, {})
									for r in res.items():
										cr.execute("UPDATE \"%s\" SET \"%s\"='%s' where id=%d"% (self._table, k, r[1],r[0]))

							# and add constraints if needed
							if isinstance(f, fields.many2one):
								#FIXME: Remove this try/except
								try:
									ref = self.pool.get(f._obj)._table
								except AttributeError:
									ref = f._obj.replace('.','_')
								# ir_actions is inherited so foreign key doesn't work on it
								if ref <> 'ir_actions':
									cr.execute("ALTER TABLE \"%s\" ADD FOREIGN KEY (\"%s\") REFERENCES \"%s\" ON DELETE %s" % (self._table, k, ref, f.ondelete))
							if f.select:
								cr.execute("CREATE INDEX \"%s_%s_index\" ON \"%s\" (\"%s\")" % (self._table, k, self._table, k))
							if f.required:
								cr.commit()
								try:
									cr.execute("ALTER TABLE \"%s\" ALTER COLUMN \"%s\" SET NOT NULL" % (self._table, k))
								except:
									logger.notifyChannel('init', netsvc.LOG_WARNING, 'WARNING: unable to set column %s of table %s not null !\nTry to re-run: tinyerp-server.py --update=module\nIf it doesn\'t work, update records and execute manually:\nALTER TABLE %s ALTER COLUMN %s SET NOT NULL' % (k, self._table, self._table, k))
							cr.commit()
					elif len(res)==1:
						f_pg_def = res[0]
						f_pg_type = f_pg_def['typname']
						f_pg_size = f_pg_def['size']
						f_pg_notnull = f_pg_def['attnotnull']
						if isinstance(f, fields.function) and not f.store:
							logger.notifyChannel('init', netsvc.LOG_WARNING, 'column %s (%s) in table %s was converted to a function !\nYou should remove this column from your database.' % (k, f.string, self._table))
							f_obj_type = None
						else:
							f_obj_type = get_pg_type(f) and get_pg_type(f)[0]

						if f_obj_type:
							if f_pg_type != f_obj_type:
								logger.notifyChannel('init', netsvc.LOG_WARNING, "column '%s' in table '%s' has changed type (DB = %s, def = %s) !" % (k, self._table, f_pg_type, f._type))
							if f_pg_type == 'varchar' and f._type == 'char' and f_pg_size != f.size:
								# columns with the name 'type' cannot be changed for an unknown reason?!
								if k != 'type':
									if f_pg_size > f.size:
										logger.notifyChannel('init', netsvc.LOG_WARNING, "column '%s' in table '%s' has changed size (DB = %d, def = %d), strings will be truncated !" % (k, self._table, f_pg_size, f.size))
#TODO: check si y a des donnees qui vont poser probleme (select char_length(...))
#TODO: issue a log message even if f_pg_size < f.size
									cr.execute("ALTER TABLE \"%s\" RENAME COLUMN \"%s\" TO temp_change_size" % (self._table,k))
									cr.execute("ALTER TABLE \"%s\" ADD COLUMN \"%s\" VARCHAR(%d)" % (self._table,k,f.size))
									cr.execute("UPDATE \"%s\" SET \"%s\"=temp_change_size::VARCHAR(%d)" % (self._table,k,f.size))
									cr.execute("ALTER TABLE \"%s\" DROP COLUMN temp_change_size" % (self._table,))
									cr.commit()
							# if the field is required and hasn't got a NOT NULL constraint
							if f.required and f_pg_notnull == 0:
								# set the field to the default value if any
								if self._defaults.has_key(k):
									default = self._defaults[k](self, cr, 1, {})
									if not (default is False):
										cr.execute("UPDATE \"%s\" SET \"%s\"='%s' WHERE %s is NULL" % (self._table, k, default, k))
										cr.commit()
								# add the NOT NULL constraint
								try:
									cr.execute("ALTER TABLE \"%s\" ALTER COLUMN \"%s\" SET NOT NULL" % (self._table, k))
									cr.commit()
								except:
									logger.notifyChannel('init', netsvc.LOG_WARNING, 'unable to set a NOT NULL constraint on column %s of the %s table !\nIf you want to have it, you should update the records and execute manually:\nALTER TABLE %s ALTER COLUMN %s SET NOT NULL' % (k, self._table, self._table, k))
								cr.commit()
							elif not f.required and f_pg_notnull == 1:
								cr.execute("ALTER TABLE \"%s\" ALTER COLUMN \"%s\" DROP NOT NULL" % (self._table,k))
								cr.commit()
							cr.execute("SELECT indexname FROM pg_indexes WHERE indexname = '%s_%s_index' and tablename = '%s'" % (self._table, k, self._table))
							res = cr.dictfetchall()
							if not res and f.select:
								cr.execute("CREATE INDEX \"%s_%s_index\" ON \"%s\" (\"%s\")" % (self._table, k, self._table, k))
								cr.commit()
							if res and not f.select:
								cr.execute("DROP INDEX \"%s_%s_index\"" % (self._table, k))
								cr.commit()
							if isinstance(f, fields.many2one):
								ref = self.pool.get(f._obj)._table
								if ref != 'ir_actions':
									cr.execute('SELECT confdeltype, conname FROM pg_constraint as con, pg_class as cl1, pg_class as cl2, ' \
												'pg_attribute as att1, pg_attribute as att2 ' \
											'WHERE con.conrelid = cl1.oid ' \
												'AND cl1.relname = %s ' \
												'AND con.confrelid = cl2.oid ' \
												'AND cl2.relname = %s ' \
												'AND array_lower(con.conkey, 1) = 1 ' \
												'AND con.conkey[1] = att1.attnum ' \
												'AND att1.attrelid = cl1.oid ' \
												'AND att1.attname = %s ' \
												'AND array_lower(con.confkey, 1) = 1 ' \
												'AND con.confkey[1] = att2.attnum ' \
												'AND att2.attrelid = cl2.oid ' \
												'AND att2.attname = %s ' \
												'AND con.contype = \'f\'', (self._table, ref, k, 'id'))
									res = cr.dictfetchall()
									if res:
										confdeltype = {
											'RESTRICT': 'r',
											'NO ACTION': 'a',
											'CASCADE': 'c',
											'SET NULL': 'n',
											'SET DEFAULT': 'd',
										}
										if res[0]['confdeltype'] != confdeltype.get(f.ondelete.upper(), 'a'):
											cr.execute('ALTER TABLE "' + self._table + '" DROP CONSTRAINT "' + res[0]['conname'] + '"')
											cr.execute('ALTER TABLE "' + self._table + '" ADD FOREIGN KEY ("' + k + '") REFERENCES "' + ref + '" ON DELETE ' + f.ondelete)
											cr.commit()
					else:
						print "ERROR"
		else:
			cr.execute("SELECT relname FROM pg_class WHERE relkind in ('r','v') AND relname='%s'" % self._table)
			create = not bool(cr.fetchone())

		for (key,con,_) in self._sql_constraints:
			cr.execute("SELECT conname FROM pg_constraint where conname='%s_%s'" % (self._table, key))
			if not cr.dictfetchall():
				try:
					cr.execute('alter table \"%s\" add constraint \"%s_%s\" %s' % (self._table,self._table,key, con,))
					cr.commit()
				except:
					logger.notifyChannel('init', netsvc.LOG_WARNING, 'unable to add \'%s\' constraint on table %s !\n If you want to have it, you should update the records and execute manually:\nALTER table %s ADD CONSTRAINT %s_%s %s' % (con, self._table, self._table,self._table,key, con,))

		if create:
			if hasattr(self,"_sql"):
				for line in self._sql.split(';'):
					line2 = line.replace('\n','').strip()
					if line2:
						cr.execute(line2)
						cr.commit()

	def __init__(self, cr):
		f=filter(lambda a: isinstance(self._columns[a], fields.function) and self._columns[a].store, self._columns)
		if f:
			list_store = []
			tuple_store = ()
			tuple_fn = ()
			for store_field in f:
				if not self._columns[store_field].store == True:
					dict_store = self._columns[store_field].store
					key = dict_store.keys()
					list_data=[]
					for i in key:
						tuple_store=self._name,store_field,self._columns[store_field]._fnct.__name__,tuple(dict_store[i][0]),dict_store[i][1],i
						list_data.append(tuple_store)
					#tuple_store=self._name,store_field,self._columns[store_field]._fnct.__name__,tuple(dict_store[key[0]][0]),dict_store[key[0]][1]
					for l in list_data:
						list_store=[]
						if l[5] in self.pool._store_function.keys():
							self.pool._store_function[l[5]].append(l)
							temp_list = list(set(self.pool._store_function[l[5]]))
							self.pool._store_function[l[5]]=temp_list
						else:
							list_store.append(l)
							self.pool._store_function[l[5]]=list_store

		if not self._table:
			self._table=self._name.replace('.','_')
		if not self._description:
			self._description = self._name
		for (key,_,msg) in self._sql_constraints:
			self.pool._sql_error[self._table+'_'+key] = msg

		# Load manual fields

		cr.execute("select id from ir_model_fields where name=%s and model=%s", ('state','ir.model.fields'))
		if cr.fetchone():
			cr.execute('select * from ir_model_fields where model=%s and state=%s', (self._name,'manual'))
			for field in cr.dictfetchall():
				if field['name'] in self._columns:
					continue
				attrs = {
					'string': field['field_description'],
					'required': bool(field['required']),
					'readonly': bool(field['readonly']),
					'domain': field['domain'] or None,
					'size': field['size'],
					'ondelete': field['on_delete'],
					'translate': (field['translate']),
					#'select': int(field['select_level'])
				}
				#if field['relation']:
				#	attrs['relation'] = field['relation']
				if field['ttype'] == 'selection':
					self._columns[field['name']] = getattr(fields, field['ttype'])(eval(field['selection']), **attrs)
				elif field['ttype'] == 'many2one':
					self._columns[field['name']] = getattr(fields, field['ttype'])(field['relation'], **attrs)
				else:
					self._columns[field['name']] = getattr(fields, field['ttype'])(**attrs)

		self._inherits_reload()
		if not self._sequence:
			self._sequence = self._table+'_id_seq'
		for k in self._defaults:
			assert (k in self._columns) or (k in self._inherit_fields), 'Default function defined in %s but field %s does not exist !' % (self._name, k,)
		for f in self._columns:
			self._columns[f].restart()

	#
	# Update objects that uses this one to update their _inherits fields
	#
	def _inherits_reload_src(self):
		for obj in self.pool.obj_pool.values():
			if self._name in obj._inherits:
				obj._inherits_reload()

	def _inherits_reload(self):
		res = {}
		for table in self._inherits:
			res.update(self.pool.get(table)._inherit_fields)
			for col in self.pool.get(table)._columns.keys():
				res[col]=(table, self._inherits[table], self.pool.get(table)._columns[col])
			for col in self.pool.get(table)._inherit_fields.keys():
				res[col]=(table, self._inherits[table], self.pool.get(table)._inherit_fields[col][2])
		self._inherit_fields=res
		self._inherits_reload_src()

	def browse(self, cr, uid, select, context=None, list_class=None):
		if not context:
			context={}
		self._list_class = list_class or browse_record_list
		cache = {}
		# need to accepts ints and longs because ids coming from a method
		# launched by button in the interface have a type long...
		if isinstance(select, (int, long)):
			return browse_record(cr,uid,select,self,cache, context=context, list_class=self._list_class)
		elif isinstance(select,list):
			return self._list_class([browse_record(cr,uid,id,self,cache, context=context, list_class=self._list_class) for id in select], context)
		else:
			return browse_null()

	def __export_row(self, cr, uid, row, fields, context=None):
		lines = []
		data = map(lambda x: '', range(len(fields)))
		done = []
		for fpos in range(len(fields)):
			f = fields[fpos]
			if f:
				r = row
				i = 0
				while i<len(f):
					r = r[f[i]]
					if not r:
						break
					if isinstance(r, (browse_record_list, list)):
						first = True
						fields2 = map(lambda x: (x[:i+1]==f[:i+1] and x[i+1:]) \
								or [], fields)
						if fields2 in done:
							break
						done.append(fields2)
						for row2 in r:
							lines2 = self.__export_row(cr, uid, row2, fields2,
									context)
							if first:
								for fpos2 in range(len(fields)):
									if lines2 and lines2[0][fpos2]:
										data[fpos2] = lines2[0][fpos2]
								lines+= lines2[1:]
								first = False
							else:
								lines+= lines2
						break
					i+=1
				if i==len(f):
					data[fpos] = str(r or '')
		return [data] + lines

	def export_data(self, cr, uid, ids, fields, context=None):
		if not context:
			context={}
		fields = map(lambda x: x.split('/'), fields)
		datas = []
		for row in self.browse(cr, uid, ids, context):
			datas += self.__export_row(cr, uid, row, fields, context)
		return datas

	def import_data(self, cr, uid, fields, datas, mode='init',
			current_module=None, noupdate=False, context=None):
		if not context:
			context={}
		fields = map(lambda x: x.split('/'), fields)
		logger = netsvc.Logger()
		def process_liness(self, datas, prefix, fields_def, position=0):
			line = datas[position]
			row = {}
			translate = {}
			todo = []
			warning = ''
			data_id= False
			#
			# Import normal fields
			#
			for i in range(len(fields)):
				if i>=len(line):
					raise Exception, 'Please check that all your lines have %d cols.' % (len(fields),)
				field = fields[i]
				if field == ["id"]:
					data_id= line[i]
					continue
				if (len(field)==len(prefix)+1) and field[len(prefix)].endswith(':id'):
					res_id = False
					if line[i]:
						if fields_def[field[len(prefix)][:-3]]['type']=='many2many':
							res_id = []
							for word in line[i].split(','):
								if '.' in word:
									module, xml_id = word.rsplit('.', 1)
								else:
									module, xml_id = current_module, word
								ir_model_data_obj = self.pool.get('ir.model.data')
								id = ir_model_data_obj._get_id(cr, uid, module,
										xml_id)
								res_id2 = ir_model_data_obj.read(cr, uid, [id],
										['res_id'])[0]['res_id']
								if res_id2:
									res_id.append(res_id2)
							if len(res_id):
								res_id=[(6,0,res_id)]
						else:
							if '.' in line[i]:
								module, xml_id = line[i].rsplit('.', 1)
							else:
								module, xml_id = current_module, line[i]
							ir_model_data_obj = self.pool.get('ir.model.data')
							id = ir_model_data_obj._get_id(cr, uid, module, xml_id)
							res_id = ir_model_data_obj.read(cr, uid, [id],
									['res_id'])[0]['res_id']
					row[field[0][:-3]] = res_id or False
					continue
				if (len(field) == len(prefix)+1) and \
						len(field[len(prefix)].split(':lang=')) == 2:
					f, lang = field[len(prefix)].split(':lang=')
					translate.setdefault(lang, {})[f]=line[i] or False
					continue
				if (len(field) == len(prefix)+1) and \
						(prefix == field[0:len(prefix)]):
					if fields_def[field[len(prefix)]]['type'] == 'integer':
						res =line[i] and int(line[i])
					elif fields_def[field[len(prefix)]]['type'] == 'float':
						res =line[i] and float(line[i])
					elif fields_def[field[len(prefix)]]['type'] == 'selection':
						res = False
						if isinstance(fields_def[field[len(prefix)]]['selection'],
								(tuple, list)):
							sel = fields_def[field[len(prefix)]]['selection']
						else:
							sel = fields_def[field[len(prefix)]]['selection'](self,
									cr, uid, context)
						for key, val in sel:
							if str(key) == line[i]:
								res = key
						if line[i] and not res:
							logger.notifyChannel("import", netsvc.LOG_WARNING,
									"key '%s' not found in selection field '%s'" % \
											(line[i], field[len(prefix)]))
					elif fields_def[field[len(prefix)]]['type']=='many2one':
						res = False
						if line[i]:
							relation = fields_def[field[len(prefix)]]['relation']
							res2 = self.pool.get(relation).name_search(cr, uid,
									line[i], [], operator='=')
							res = (res2 and res2[0][0]) or False
							if not res:
								warning += ('Relation not found: ' + line[i] + \
										' on ' + relation + ' !\n')
								logger.notifyChannel("import", netsvc.LOG_WARNING,
										'Relation not found: ' + line[i] + \
												' on ' + relation + ' !\n')
					elif fields_def[field[len(prefix)]]['type']=='many2many':
						res = []
						if line[i]:
							relation = fields_def[field[len(prefix)]]['relation']
							for word in line[i].split(','):
								res2 = self.pool.get(relation).name_search(cr,
										uid, word, [], operator='=')
								res3 = (res2 and res2[0][0]) or False
								if not res3:
									warning += ('Relation not found: ' + \
											line[i] + ' on '+relation + ' !\n')
									logger.notifyChannel("import",
											netsvc.LOG_WARNING,
											'Relation not found: ' + line[i] + \
													' on '+relation + ' !\n')
								else:
									res.append(res3)
							if len(res):
								res= [(6,0,res)]
					else:
						res = line[i] or False
					row[field[len(prefix)]] = res
				elif (prefix==field[0:len(prefix)]):
					if field[0] not in todo:
						todo.append(field[len(prefix)])
			#
			# Import one2many fields
			#
			nbrmax = 1
			for field in todo:
				newfd = self.pool.get(fields_def[field]['relation']).fields_get(
						cr, uid, context=context)
				res = process_liness(self, datas, prefix + [field], newfd, position)
				(newrow, max2, w2, translate2, data_id2) = res
				nbrmax = max(nbrmax, max2)
				warning = warning + w2
				reduce(lambda x,y: x and y, newrow)
				row[field] = (reduce(lambda x, y: x or y, newrow.values()) and \
						[(0,0,newrow)]) or []
				i = max2
				while (position+i)<len(datas):
					ok = True
					for j in range(len(fields)):
						field2 = fields[j]
						if (len(field2) <= (len(prefix)+1)) and datas[position+i][j]:
							ok = False
					if not ok:
						break

					(newrow, max2, w2, translate2, data_id2) = process_liness(
							self, datas, prefix+[field], newfd, position+i)
					warning = warning+w2
					if reduce(lambda x,y: x or y, newrow.values()):
						row[field].append((0,0,newrow))
					i+=max2
					nbrmax = max(nbrmax, i)

			if len(prefix)==0:
				for i in range(max(nbrmax,1)):
					#if datas:
					datas.pop(0)
			result = (row, nbrmax, warning, translate, data_id)
			return result

		fields_def = self.fields_get(cr, uid, context=context)
		done = 0

		while len(datas):
			res = {}
			try:
				(res, other, warning, translate, data_id) = \
						process_liness(self, datas, [], fields_def)
				if warning:
					cr.rollback()
					return (-1, res, warning, '')
				id= self.pool.get('ir.model.data')._update(cr, uid, self._name,
						current_module, res, xml_id=data_id, mode=mode,
						noupdate=noupdate)
				for lang in translate:
					context2=context.copy()
					context2['lang']=lang
					self.write(cr, uid, [id], translate[lang], context2)
			except Exception, e:
				logger.notifyChannel("import",netsvc.LOG_ERROR, e)
				cr.rollback()
				try:
					return (-1, res, e[0], warning)
				except:
					return (-1, res, e[0], '')
			done += 1
		#
		# TODO: Send a request with the result and multi-thread !
		#
		return (done, 0, 0, 0)

	def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
		if not context:
			context={}
		self.pool.get('ir.model.access').check(cr, user, self._name, 'read')
		if not fields:
			fields = self._columns.keys() + self._inherit_fields.keys()
		select = ids
		if isinstance(ids, (int, long)):
			select = [ids]
		result =  self._read_flat(cr, user, select, fields, context, load)
		for r in result:
			for key,v in r.items():
				if v == None:
					r[key]=False
		if isinstance(ids, (int, long)):
			return result[0]
		return result

	def _read_flat(self, cr, user, ids, fields, context=None, load='_classic_read'):
		if not context:
			context={}
		if not ids:
			return []

		if fields==None:
			fields = self._columns.keys()

		# construct a clause for the rules :
		d1, d2 = self.pool.get('ir.rule').domain_get(cr, user, self._name)

		# all inherited fields + all non inherited fields for which the attribute whose name is in load is True
		fields_pre = filter(lambda x: x in self._columns and getattr(self._columns[x],'_classic_write'), fields) + self._inherits.values()

		res = []
		if len(fields_pre) :
			fields_pre2 = map(lambda x: (x in ('create_date', 'write_date')) and ('date_trunc(\'second\', '+x+') as '+x) or '"'+x+'"', fields_pre)
			for i in range((len(ids) / ID_MAX) + ((len(ids) % ID_MAX) and 1 or 0)):
				sub_ids = ids[ID_MAX * i:ID_MAX * (i + 1)]
				if d1:
					cr.execute('select %s from \"%s\" where id in (%s) and %s order by %s' % \
							(','.join(fields_pre2 + ['id']), self._table,
								','.join([str(x) for x in sub_ids]), d1,
								self._order),d2)
					if not cr.rowcount == len({}.fromkeys(sub_ids)):
						raise except_orm('AccessError',
								'You try to bypass an access rule (Document type: %s).' % self._description)
				else:
					cr.execute('select %s from \"%s\" where id in (%s) order by %s' % \
							(','.join(fields_pre2 + ['id']), self._table,
								','.join([str(x) for x in sub_ids]),
								self._order))
				res.extend(cr.dictfetchall())
		else:
			res = map(lambda x: {'id': x}, ids)

		for f in fields_pre:
			if self._columns[f].translate:
				ids = map(lambda x: x['id'], res)
				res_trans = self.pool.get('ir.translation')._get_ids(cr, user, self._name+','+f, 'model', context.get('lang', False) or 'en_US', ids)
				for r in res:
					r[f] = res_trans.get(r['id'], False) or r[f]

		for table in self._inherits:
			col = self._inherits[table]
			cols = intersect(self._inherit_fields.keys(), fields)
			if not cols:
				continue
			res2 = self.pool.get(table).read(cr, user, [x[col] for x in res], cols, context, load)

			res3 = {}
			for r in res2:
				res3[r['id']] = r
				del r['id']

			for record in res:
				record.update(res3[record[col]])
				if col not in fields:
					del record[col]

		# all fields which need to be post-processed by a simple function (symbol_get)
		fields_post = filter(lambda x: x in self._columns and self._columns[x]._symbol_get, fields)
		if fields_post:
			# maybe it would be faster to iterate on the fields then on res, so that we wouldn't need
			# to get the _symbol_get in each occurence
			for r in res:
				for f in fields_post:
					r[f] = self.columns[f]._symbol_get(r[f])
		ids = map(lambda x: x['id'], res)

		# all non inherited fields for which the attribute whose name is in load is False
		fields_post = filter(lambda x: x in self._columns and not getattr(self._columns[x], load), fields)
		for f in fields_post:
			# get the value of that field for all records/ids
			res2 = self._columns[f].get(cr, self, ids, f, user, context=context, values=res)
			for record in res:
				record[f] = res2[record['id']]
				
		readonly = None
		for vals in res:
			for field in vals.copy():
				fobj = None
				if field in self._columns:
					fobj = self._columns[field]

				if not fobj:
					continue
				groups = fobj.read
				if groups:
					edit = False
					for group in groups:
						module = group.split(".")[0]
						grp = group.split(".")[1]
						cr.execute("select count(*) from res_groups_users_rel where gid in (select res_id from ir_model_data where name='%s' and module='%s' and model='%s') and uid=%s" % \
								   (grp, module, 'res.groups', user))
						readonly = cr.fetchall()
						if readonly[0][0] >= 1:
							edit = True
							break
						elif readonly[0][0] == 0:
							edit = False
						else:
							edit = False

					if not edit:
						if type(vals[field]) == type([]):
							vals[field] = []
						elif type(vals[field]) == type(0.0):
							vals[field] = 0
						elif type(vals[field]) == type(''):
							vals[field] = '=No Permission='
						else:
							vals[field] = False
		return res

	def _validate(self, cr, uid, ids):
		field_error = []
		field_err_str = []
		for field in self._constraints:
			if not field[0](self, cr, uid, ids):
				if len(field)>1:
					field_error+=field[2]
				field_err_str.append(field[1])
		if len(field_err_str):
			cr.rollback()
			raise except_orm('ValidateError', ('\n'.join(field_err_str), ','.join(field_error)))

	def default_get(self, cr, uid, fields_list, context=None):
		if not context:
			context={}
		value = {}
		# get the default values for the inherited fields
		for t in self._inherits.keys():
			value.update(self.pool.get(t).default_get(cr, uid, fields_list,
				context))

		# get the default values defined in the object
		for f in fields_list:
			if f in self._defaults:
				value[f] = self._defaults[f](self, cr, uid, context)
			fld_def = ((f in self._columns) and self._columns[f]) \
					or ((f in self._inherit_fields ) and self._inherit_fields[f][2]) \
					or False
			if isinstance(fld_def, fields.property):
				property_obj = self.pool.get('ir.property')
				definition_id = fld_def._field_get(cr, uid, self._name, f)
				nid = property_obj.search(cr, uid, [('fields_id', '=',
					definition_id), ('res_id', '=', False)])
				if nid:
					prop_value = property_obj.browse(cr, uid, nid[0],
							context=context).value
					value[f] = (prop_value and int(prop_value.split(',')[1])) \
							or False

		# get the default values set by the user and override the default
		# values defined in the object
		ir_values_obj = self.pool.get('ir.values')
		res = ir_values_obj.get(cr, uid, 'default', False, [self._name])
		for id, field, field_value in res:
			if field in fields_list:
				fld_def = (field in self._columns) and self._columns[field] or self._inherit_fields[field][2]
				if fld_def._type in ('many2one', 'one2one'):
					obj = self.pool.get(fld_def._obj)
					if not obj.search(cr, uid, [('id', '=', field_value)]):
						continue
				if fld_def._type in ('many2many'):
					obj = self.pool.get(fld_def._obj)
					field_value2 = []
					for i in range(len(field_value)):
						if not obj.search(cr, uid, [('id', '=',
							field_value[i])]):
							continue
						field_value2.append(field_value[i])
					field_value = field_value2
				if fld_def._type in ('one2many'):
					obj = self.pool.get(fld_def._obj)
					field_value2 = []
					for i in range(len(field_value)):
						field_value2.append({})
						for field2 in field_value[i]:
							if obj._columns[field2]._type in ('many2one', 'one2one'):
								obj2 = self.pool.get(obj._columns[field2]._obj)
								if not obj2.search(cr, uid,
										[('id', '=', field_value[i][field2])]):
									continue
							# TODO add test for many2many and one2many
							field_value2[i][field2] = field_value[i][field2]
					field_value = field_value2
				value[field] = field_value
		return value

	def perm_read(self, cr, user, ids, context=None, details=True):
		if not context:
			context={}
		if not ids:
			return []
		fields = ', p.level, p.uid, p.gid'
		if self._log_access:
			fields +=', u.create_uid, u.create_date, u.write_uid, u.write_date'
		if isinstance(ids, (int, long)):
			ids_str = str(ids)
		else:
			ids_str = string.join(map(lambda x:str(x), ids),',')
		cr.execute('select u.id'+fields+' from perm p right join "'+self._table+'" u on u.perm_id=p.id where u.id in ('+ids_str+')')
		res = cr.dictfetchall()
#		for record in res:
#			for f in ('ox','ux','gx','uid','gid'):
#				if record[f]==None:
#					record[f]=False
		for r in res:
			for key in r:
				r[key] = r[key] or False
				if key in ('write_uid','create_uid','uid') and details:
					if r[key]:
						r[key] = self.pool.get('res.users').name_get(cr, user, [r[key]])[0]
		if isinstance(ids, (int, long)):
			return res[ids]
		return res

	def unlink(self, cr, uid, ids, context=None):
		if not context:
			context={}
		if not ids:
			return True
		if isinstance(ids, (int, long)):
			ids = [ids]

		fn_list = []
		if self._name in self.pool._store_function.keys():
			list_store = self.pool._store_function[self._name]
			fn_data = ()
			id_change = []
			for tuple_fn in list_store:
				for id in ids:
					id_change.append(self._store_get_ids(cr, uid, id,tuple_fn, context)[0])
				fn_data = id_change,tuple_fn
				fn_list.append(fn_data)

		delta= context.get('read_delta',False)
		if delta and self._log_access:
			for i in range((len(ids) / ID_MAX) + ((len(ids) % ID_MAX) and 1 or 0)):
				sub_ids = ids[ID_MAX * i:ID_MAX * (i + 1)]
				cr.execute("select  (now()  - min(write_date)) <= '%s'::interval " \
						"from \"%s\" where id in (%s)" %
						(delta, self._table, ",".join(map(str, sub_ids))) )
			res= cr.fetchone()
			if res and res[0]:
				raise except_orm('ConcurrencyException',
						'This record was modified in the meanwhile')

		self.pool.get('ir.model.access').check(cr, uid, self._name, 'unlink')

		wf_service = netsvc.LocalService("workflow")
		for id in ids:
			wf_service.trg_delete(uid, self._name, id, cr)

		#cr.execute('select * from '+self._table+' where id in ('+str_d+')', ids)
		#res = cr.dictfetchall()
		#for key in self._inherits:
		#	ids2 = [x[self._inherits[key]] for x in res]
		#	self.pool.get(key).unlink(cr, uid, ids2)

		d1, d2 = self.pool.get('ir.rule').domain_get(cr, uid, self._name)
		if d1:
			d1 = ' AND '+d1

		for i in range((len(ids) / ID_MAX) + ((len(ids) % ID_MAX) and 1 or 0)):
			sub_ids = ids[ID_MAX * i:ID_MAX * (i + 1)]
			str_d = string.join(('%d',)*len(sub_ids),',')
			if d1:
				cr.execute('SELECT id FROM "'+self._table+'" ' \
						'WHERE id IN ('+str_d+')'+d1, sub_ids+d2)
				if not cr.rowcount == len({}.fromkeys(ids)):
					raise except_orm('AccessError',
							'You try to bypass an access rule (Document type: %s).' % \
									self._description)

			cr.execute('delete from inherit ' \
					'where (obj_type=%s and obj_id in ('+str_d+')) ' \
						'or (inst_type=%s and inst_id in ('+str_d+'))',
						(self._name,)+tuple(sub_ids)+(self._name,)+tuple(sub_ids))
			if d1:
				cr.execute('delete from "'+self._table+'" ' \
						'where id in ('+str_d+')'+d1, sub_ids+d2)
			else:
				cr.execute('delete from "'+self._table+'" ' \
						'where id in ('+str_d+')', sub_ids)
		if fn_list:
			for ids,tuple_fn in fn_list:
				self._store_set_values(cr, uid, ids,tuple_fn,id_change, context)

		return True

	#
	# TODO: Validate
	#
	def write(self, cr, user, ids, vals, context=None):
		readonly = None
		for field in vals.copy():
			fobj = None
			if field in self._columns:
				fobj = self._columns[field]
			else:
				fobj = self._inherit_fields[field][2]
			if not fobj:
				continue
			groups = fobj.write
				
			if groups:
				edit = False
				for group in groups:
					module = group.split(".")[0]
					grp = group.split(".")[1]
					cr.execute("select count(*) from res_groups_users_rel where gid in (select res_id from ir_model_data where name='%s' and module='%s' and model='%s') and uid=%s" % \
							   (grp, module, 'res.groups', user))
					readonly = cr.fetchall()
					if readonly[0][0] >= 1:
						edit = True
						break
					elif readonly[0][0] == 0:
						edit = False
					else:
						edit = False

				if not edit:
					vals.pop(field)

		if not context:
			context={}
		if not ids:
			return True
		if isinstance(ids, (int, long)):
			ids = [ids]
		delta= context.get('read_delta',False)
		if delta and self._log_access:
			for i in range((len(ids) / ID_MAX) + ((len(ids) % ID_MAX) and 1 or 0)):
				sub_ids = ids[ID_MAX * i:ID_MAX * (i + 1)]
				cr.execute("select  (now()  - min(write_date)) <= '%s'::interval " \
						"from %s where id in (%s)" %
						(delta,self._table, ",".join(map(str, sub_ids))))
				res= cr.fetchone()
				if res and res[0]:
					for field in vals:
						if field in self._columns and self._columns[field]._classic_write:
							raise except_orm('ConcurrencyException',
									'This record was modified in the meanwhile')

		self.pool.get('ir.model.access').check(cr, user, self._name, 'write')

		#for v in self._inherits.values():
		#	assert v not in vals, (v, vals)
		upd0=[]
		upd1=[]
		upd_todo=[]
		updend=[]
		direct = []
		totranslate = context.get('lang', False) and (context['lang'] != 'en_US')
		for field in vals:
			if field in self._columns:
				if self._columns[field]._classic_write:
					if (not totranslate) or not self._columns[field].translate:
						upd0.append('"'+field+'"='+self._columns[field]._symbol_set[0])
						upd1.append(self._columns[field]._symbol_set[1](vals[field]))
					direct.append(field)
				else:
					upd_todo.append(field)
			else:
				updend.append(field)
			if field in self._columns \
					and hasattr(self._columns[field], 'selection') \
					and vals[field]:
				if self._columns[field]._type == 'reference':
					val = vals[field].split(',')[0]
				else:
					val = vals[field]
				if isinstance(self._columns[field].selection, (tuple, list)):
					if val not in dict(self._columns[field].selection):
						raise except_orm('ValidateError',
						'The value "%s" for the field "%s" is not in the selection' \
								% (vals[field], field))
				else:
					if val not in dict(self._columns[field].selection(
						self, cr, user, context=context)):
						raise except_orm('ValidateError',
						'The value "%s" for the field "%s" is not in the selection' \
								% (vals[field], field))

		if self._log_access:
			upd0.append('write_uid=%d')
			upd0.append('write_date=now()')
			upd1.append(user)

		if len(upd0):

			d1, d2 = self.pool.get('ir.rule').domain_get(cr, user, self._name)
			if d1:
				d1 = ' and '+d1

			for i in range((len(ids) / ID_MAX) + ((len(ids) % ID_MAX) and 1 or 0)):
				sub_ids = ids[ID_MAX * i:ID_MAX * (i + 1)]
				ids_str = string.join(map(str, sub_ids),',')
				if d1:
					cr.execute('SELECT id FROM "'+self._table+'" ' \
							'WHERE id IN ('+ids_str+')'+d1, d2)
					if not cr.rowcount == len({}.fromkeys(sub_ids)):
						raise except_orm('AccessError',
								'You try to bypass an access rule (Document type: %s).'% \
										self._description)
				else:
					cr.execute('SELECT id FROM "'+self._table+'" WHERE id IN ('+ids_str+')')
					if not cr.rowcount == len({}.fromkeys(sub_ids)):
						raise except_orm('AccessError',
								'You try to write on an record that doesn\'t exist ' \
										'(Document type: %s).' % self._description)
				if d1:
					cr.execute('update "'+self._table+'" set '+string.join(upd0,',')+' ' \
							'where id in ('+ids_str+')'+d1, upd1+ d2)
				else:
					cr.execute('update "'+self._table+'" set '+string.join(upd0,',')+' ' \
							'where id in ('+ids_str+')', upd1)

			if totranslate:
				for f in direct:
					if self._columns[f].translate:
						self.pool.get('ir.translation')._set_ids(cr, user, self._name+','+f,'model',  context['lang'], ids,vals[f])

		# call the 'set' method of fields which are not classic_write
		upd_todo.sort(lambda x,y: self._columns[x].priority-self._columns[y].priority)
		for field in upd_todo:
			for id in ids:
				self._columns[field].set(cr, self, id, field, vals[field], user, context=context)

		for table in self._inherits:
			col = self._inherits[table]
			nids = []
			for i in range((len(ids) / ID_MAX) + ((len(ids) % ID_MAX) and 1 or 0)):
				sub_ids = ids[ID_MAX * i:ID_MAX * (i + 1)]
				ids_str = string.join(map(str, sub_ids),',')
				cr.execute('select distinct "'+col+'" from "'+self._table+'" ' \
						'where id in ('+ids_str+')', upd1)
				nids.extend([x[0] for x in cr.fetchall()])

			v = {}
			for val in updend:
				if self._inherit_fields[val][0]==table:
					v[val]=vals[val]
			self.pool.get(table).write(cr, user, nids, v, context)

		self._validate(cr, user, ids)

		if context.has_key('read_delta'):
			del context['read_delta']

		wf_service = netsvc.LocalService("workflow")
		for id in ids:
			wf_service.trg_write(user, self._name, id, cr)
		self._update_function_stored(cr, user, ids, context=context)

		if self._name in self.pool._store_function.keys():
			list_store = self.pool._store_function[self._name]
			for tuple_fn in list_store:
				flag = False
				if not tuple_fn[3]:
					flag = True
				for field in tuple_fn[3]:
					if field in vals.keys():
						flag = True
						break
				if flag:
					id_change = self._store_get_ids(cr, user, ids[0],tuple_fn, context)
					self._store_set_values(cr, user, ids[0],tuple_fn,id_change, context)

		return True

	#
	# TODO: Should set perm to user.xxx
	#
	def create(self, cr, user, vals, context=None):
		""" create(cr, user, vals, context) -> int
		cr = database cursor
		user = user id
		vals = dictionary of the form {'field_name':field_value, ...}
		"""
		if not context:
			context={}
		self.pool.get('ir.model.access').check(cr, user, self._name, 'create')

		default = []

		avoid_table = []
		for (t,c) in self._inherits.items():
			if c in vals:
				avoid_table.append(t)
		for f in self._columns.keys(): # + self._inherit_fields.keys():
			if not f in vals:
				default.append(f)
		for f in self._inherit_fields.keys():
			if (not f in vals) and (not self._inherit_fields[f][0] in avoid_table):
				default.append(f)

		if len(default):
			vals.update(self.default_get(cr, user, default, context))

		tocreate = {}
		for v in self._inherits:
			if self._inherits[v] not in vals:
				tocreate[v] = {}

		#cr.execute('select perm_id from res_users where id=%d', (user,))
		perm = False #cr.fetchone()[0]
		(upd0, upd1, upd2) = ('', '', [])
		upd_todo = []

		for v in vals.keys():
			if v in self._inherit_fields:
				(table,col,col_detail) = self._inherit_fields[v]
				tocreate[table][v] = vals[v]
				del vals[v]

		cr.execute("select nextval('"+self._sequence+"')")
		id_new = cr.fetchone()[0]
		for table in tocreate:
			id = self.pool.get(table).create(cr, user, tocreate[table])
			upd0 += ','+self._inherits[table]
			upd1 += ',%d'
			upd2.append(id)
			cr.execute('insert into inherit (obj_type,obj_id,inst_type,inst_id) values (%s,%d,%s,%d)', (table,id,self._name,id_new))

		for field in vals:
			if self._columns[field]._classic_write:
				upd0=upd0+',"'+field+'"'
				upd1=upd1+','+self._columns[field]._symbol_set[0]
				upd2.append(self._columns[field]._symbol_set[1](vals[field]))
			else:
				upd_todo.append(field)
			if field in self._columns \
					and hasattr(self._columns[field], 'selection') \
					and vals[field]:
				if self._columns[field]._type == 'reference':
					val = vals[field].split(',')[0]
				else:
					val = vals[field]
				if isinstance(self._columns[field].selection, (tuple, list)):
					if val not in dict(self._columns[field].selection):
						raise except_orm('ValidateError',
						'The value "%s" for the field "%s" is not in the selection' \
								% (vals[field], field))
				else:
					if val not in dict(self._columns[field].selection(
						self, cr, user, context=context)):
						raise except_orm('ValidateError',
						'The value "%s" for the field "%s" is not in the selection' \
								% (vals[field], field))
		if self._log_access:
			upd0 += ',create_uid,create_date'
			upd1 += ',%d,now()'
			upd2.append(user)
		cr.execute('insert into "'+self._table+'" (id,perm_id'+upd0+") values ("+str(id_new)+',NULL'+upd1+')', tuple(upd2))
		upd_todo.sort(lambda x,y: self._columns[x].priority-self._columns[y].priority)
		for field in upd_todo:
			self._columns[field].set(cr, self, id_new, field, vals[field], user, context)

		self._validate(cr, user, [id_new])

		wf_service = netsvc.LocalService("workflow")
		wf_service.trg_create(user, self._name, id_new, cr)
		self._update_function_stored(cr, user, [id_new], context=context)
		if self._name in self.pool._store_function.keys():
			list_store = self.pool._store_function[self._name]
			for tuple_fn in list_store:
				id_change = self._store_get_ids(cr, user, id_new,tuple_fn, context)
				self._store_set_values(cr, user, id_new,tuple_fn,id_change, context)

		return id_new

	def _store_get_ids(self,cr, uid, ids,tuple_fn, context):
		parent_id=getattr(self.pool.get(tuple_fn[0]),tuple_fn[4].func_name)(cr,uid,[ids])
		return parent_id

	def _store_set_values(self,cr,uid,ids,tuple_fn,parent_id,context):
		name = tuple_fn[1]
		table = tuple_fn[0]
		args={}
		vals_tot=getattr(self.pool.get(table),tuple_fn[2])(cr, uid, parent_id ,name, args, context)
		write_dict = {}
		for id in vals_tot.keys():
			write_dict[name]=vals_tot[id]
			self.pool.get(table).write(cr,uid,[id],write_dict)
		return True

	def _update_function_stored(self, cr, user, ids, context=None):
		if not context:
			context = {}
		f = filter(lambda a: isinstance(self._columns[a], fields.function) \
				and self._columns[a].store, self._columns)
		if f:
			result=self.read(cr, user, ids, fields=f, context=context)
			for res in result:
				upd0=[]
				upd1=[]
				for field in res:
					if field not in f:
						continue
					value = res[field]
					if self._columns[field]._type in ('many2one', 'one2one'):
						value = res[field][0]
					upd0.append('"'+field+'"='+self._columns[field]._symbol_set[0])
					upd1.append(self._columns[field]._symbol_set[1](value))
				upd1.append(res['id'])
				cr.execute('update "' + self._table + '" set ' + \
						string.join(upd0, ',') + ' where id = %d', upd1)
		return True

	#
	# TODO: Validate
	#
	def perm_write(self, cr, user, ids, fields, context=None):
		if not context:
			context={}
		if not ids:
			return True
		if isinstance(ids, (int, long)):
			ids = [ids]
		query = []
		vals = []
		keys = []
		for x in fields.keys():
			query.append('"'+x+'"=%d')
			vals.append(fields[x])
			keys.append('"'+x+'"')
		cr.execute('select id from perm where ' + ' and '.join(query) + ' limit 1', vals)
		res = cr.fetchone()
		if res:
			id = res[0]
		else:
			cr.execute("select nextval('perm_id_seq')")
			id = cr.fetchone()[0]
			cr.execute('insert into perm (id,' + ','.join(keys) + ') values (' + str(id) + ',' + ('%d,'*(len(keys)-1)+'%d')+')', vals)
		ids_str = ','.join(map(str, ids))
		cr.execute('update '+self._table+' set perm_id=%d where id in ('+ids_str+')', (id,))
		return True

	# returns the definition of each field in the object
	# the optional fields parameter can limit the result to some fields
	def fields_get(self, cr, user, fields=None, context=None):
		if context is None:
			context = {}
		res = {}
		translation_obj = self.pool.get('ir.translation')
		model_access_obj = self.pool.get('ir.model.access')
		for parent in self._inherits:
			res.update(self.pool.get(parent).fields_get(cr, user, fields,
				context))
		read_access= model_access_obj.check(cr, user, self._name, 'write',
				raise_exception=False)
		for f in self._columns.keys():
			res[f] = {'type': self._columns[f]._type}
			for arg in ('string', 'readonly', 'states', 'size', 'required',
					'change_default', 'translate', 'help', 'select'):
				if getattr(self._columns[f], arg):
					res[f][arg] = getattr(self._columns[f], arg)
			if not read_access:
				res[f]['readonly']= True
				res[f]['states'] = {}
			for arg in ('digits', 'invisible'):
				if hasattr(self._columns[f], arg) \
						and getattr(self._columns[f], arg):
					res[f][arg] = getattr(self._columns[f], arg)

			# translate the field label
			res_trans = translation_obj._get_source(cr, user,
					self._name + ',' + f, 'field', context.get('lang', False) or 'en_US')
			if res_trans:
				res[f]['string'] = res_trans
			help_trans = translation_obj._get_source(cr, user,
					self._name + ',' + f, 'help', context.get('lang', False) or 'en_US')
			if help_trans:
				res[f]['help'] = help_trans

			if hasattr(self._columns[f], 'selection'):
				if isinstance(self._columns[f].selection, (tuple, list)):
					sel = self._columns[f].selection
					# translate each selection option
					sel2 = []
					for (key,val) in sel:
						val2 = translation_obj._get_source(cr, user,
								self._name + ',' + f, 'selection',
								context.get('lang', False) or 'en_US', val)
						sel2.append((key, val2 or val))
					sel = sel2
					res[f]['selection'] = sel
				else:
					# call the 'dynamic selection' function
					res[f]['selection'] = self._columns[f].selection(self, cr,
							user, context)
			if res[f]['type'] in ('one2many', 'many2many',
					'many2one', 'one2one'):
				res[f]['relation'] = self._columns[f]._obj
				res[f]['domain'] = self._columns[f]._domain
				res[f]['context'] = self._columns[f]._context

		if fields:
			# filter out fields which aren't in the fields list
			for r in res.keys():
				if r not in fields:
					del res[r]
		return res

	#
	# Overload this method if you need a window title which depends on the context
	#
	def view_header_get(self, cr, user, view_id=None, view_type='form', context=None):
		return False

	def __view_look_dom(self, cr, user, node, context=None):
		if not context:
			context={}
		result = False
		fields = {}
		childs = True

		if node.nodeType==node.ELEMENT_NODE and node.localName=='field':
			if node.hasAttribute('name'):
				attrs = {}
				try:
					if node.getAttribute('name') in self._columns:
						relation = self._columns[node.getAttribute('name')]._obj
					else:
						relation = self._inherit_fields[node.getAttribute('name')][2]._obj
				except:
					relation = False

				if relation:
					childs = False
					views = {}
					for f in node.childNodes:
						if f.nodeType==f.ELEMENT_NODE and f.localName in ('form','tree','graph'):
							node.removeChild(f)
							xarch,xfields = self.pool.get(relation).__view_look_dom_arch(cr, user, f, context)
							views[str(f.localName)] = {
								'arch': xarch,
								'fields': xfields
							}
					attrs = {'views': views}
				fields[node.getAttribute('name')] = attrs

		elif node.nodeType==node.ELEMENT_NODE and node.localName in ('form','tree'):
			result = self.view_header_get(cr, user, False, node.localName, context)
			if result:
				node.setAttribute('string', result.decode('utf-8'))
		if node.nodeType==node.ELEMENT_NODE and node.hasAttribute('groups'):
			groups = None
			group_str = node.getAttribute('groups')
			if ',' in group_str:
				groups = group_str.split(',');
				readonly = False
				access_pool = self.pool.get('ir.model.access')
				for group in groups:
					readonly = readonly and access_pool.check_groups(cr, user, group)

				if readonly:
					parent = node.parentNode
					parent.removeChild(node)

			else:
				if not self.pool.get('ir.model.access').check_groups(cr, user, group_str):
					parent = node.parentNode
					parent.removeChild(node)

		if node.nodeType == node.ELEMENT_NODE:
			# translate view
			if ('lang' in context) and not result:
				if node.hasAttribute('string') and node.getAttribute('string'):
					trans = tools.translate(cr, user, self._name, 'view', context['lang'], node.getAttribute('string').encode('utf8'))
					if trans:
						node.setAttribute('string', trans.decode('utf8'))
				if node.hasAttribute('sum') and node.getAttribute('sum'):
					trans = tools.translate(cr, user, self._name, 'view', context['lang'], node.getAttribute('sum').encode('utf8'))
					if trans:
						node.setAttribute('sum', trans.decode('utf8'))
			#
			# Add view for properties !
			#
			if node.localName=='properties':
				parent = node.parentNode
				doc = node.ownerDocument
				models = map(lambda x: "'"+x+"'", [self._name] + self._inherits.keys())
				cr.execute('select id,name,group_name from ir_model_fields where model in ('+','.join(models)+') and view_load order by group_name, id')
				oldgroup = None
				res = cr.fetchall()
				for id, fname, gname in res:
					if oldgroup != gname:
						child = doc.createElement('separator')
						child.setAttribute('string', gname.decode('utf-8'))
						child.setAttribute('colspan', "4")
						oldgroup = gname
						parent.insertBefore(child, node)

					child = doc.createElement('field')
					child.setAttribute('name', fname.decode('utf-8'))
					parent.insertBefore(child, node)
				parent.removeChild(node)

		if childs:
			for f in node.childNodes:
				fields.update(self.__view_look_dom(cr, user, f,context))
		return fields

	def __view_look_dom_arch(self, cr, user, node, context=None):
		if not context:
			context={}
		fields_def = self.__view_look_dom(cr, user, node, context=context)

		buttons = xpath.Evaluate('//button', node)
		if buttons:
			for button in buttons:
				if button.getAttribute('type') == 'object':
					continue

				ok = True

				serv = netsvc.LocalService('object_proxy')
				user_roles = serv.execute_cr(cr, user, 'res.users', 'read', [user], ['roles_id'])[0]['roles_id']
				cr.execute("select role_id from wkf_transition where signal='%s'" % button.getAttribute('name'))
				roles = cr.fetchall()
				for role in roles:
					if role[0]:
						ok = ok and serv.execute_cr(cr, user, 'res.roles', 'check', user_roles, role[0])

				if not ok:
					button.setAttribute('readonly', '1')
				else:
					button.setAttribute('readonly', '0')

		arch = node.toxml(encoding="utf-8").replace('\t', '')

		fields = self.fields_get(cr, user, fields_def.keys(), context)
		for field in fields_def:
			fields[field].update(fields_def[field])
		return arch, fields


	def __get_default_calendar_view(self):
		"""Generate a default calendar view (For internal use only).
		"""

		arch = ('<?xml version="1.0" encoding="utf-8"?>\n'
			    '<calendar string="%s" date_start="%s"') % (self._description, self._date_name)

		if 'user_id' in self._columns:
			arch += ' color="user_id"'

		elif 'partner_id' in self._columns:
			arch += ' color="partner_id"'

		if 'date_stop' in self._columns:
			arch += ' date_stop="date_stop"'

		elif 'date_end' in self._columns:
			arch += ' date_stop="date_end"'

		elif 'date_delay' in self._columns:
			arch += ' date_delay="date_delay"'

		elif 'planned_hours' in self._columns:
			arch += ' date_delay="planned_hours"'

		arch += ('>\n'
			   	 '  <field name="%s"/>\n'
			   	 '</calendar>') % (self._rec_name)

		return arch

	#
	# if view_id, view_type is not required
	#
	def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False):
		if not context:
			context={}
		def _inherit_apply(src, inherit):
			def _find(node, node2):
				# Check if xpath query or normal inherit (with field matching)
				if node2.nodeType==node2.ELEMENT_NODE and node2.localName=='xpath':
					res = xpath.Evaluate(node2.getAttribute('expr'), node)
					return res and res[0]
				else:
					if node.nodeType==node.ELEMENT_NODE and node.localName==node2.localName:
						res = True
						for attr in node2.attributes.keys():
							if attr=='position':
								continue
							if node.hasAttribute(attr):
								if node.getAttribute(attr)==node2.getAttribute(attr):
									continue
							res = False
						if res:
							return node
					for child in node.childNodes:
						res = _find(child, node2)
						if res: return res
				return None

			doc_src = dom.minidom.parseString(src)
			doc_dest = dom.minidom.parseString(inherit)
			for node2 in doc_dest.childNodes:
				if not node2.nodeType==node2.ELEMENT_NODE:
					continue
				node = _find(doc_src, node2)
				if node:
					pos = 'inside'
					if node2.hasAttribute('position'):
						pos = node2.getAttribute('position')
					if pos=='replace':
						parent = node.parentNode
						for child in node2.childNodes:
							if child.nodeType==child.ELEMENT_NODE:
								parent.insertBefore(child, node)
						parent.removeChild(node)
					else:
						for child in node2.childNodes:
							if child.nodeType==child.ELEMENT_NODE:
								if pos=='inside':
									node.appendChild(child)
								elif pos=='after':
									sib = node.nextSibling
									if sib:
										node.parentNode.insertBefore(child, sib)
									else:
										node.parentNode.appendChild(child)
								elif pos=='before':
									node.parentNode.insertBefore(child, node)
								else:
									raise AttributeError, 'Unknown position in inherited view %s !' % pos
				else:
					attrs = ''.join([
						' %s="%s"' % (attr, node2.getAttribute(attr))
						for attr in node2.attributes.keys()
						if attr != 'position'
					])
					tag = "<%s%s>" % (node2.localName, attrs)
					raise AttributeError, "Couldn't find tag '%s' in parent view !" % tag
			return doc_src.toxml(encoding="utf-8").replace('\t', '')

		result = {'type':view_type, 'model':self._name}

		ok = True
		model = True
		sql_res = False
		while ok:
			if view_id:
				where = (model and (" and model='%s'" % (self._name,))) or ''
				cr.execute('select arch,name,field_parent,id,type,inherit_id from ir_ui_view where id=%d'+where, (view_id,))
			else:
				cr.execute('select arch,name,field_parent,id,type,inherit_id from ir_ui_view where model=%s and type=%s order by priority', (self._name,view_type))
			sql_res = cr.fetchone()
			if not sql_res:
				break
			ok = sql_res[5]
			view_id = ok or sql_res[3]
			model = False

		# if a view was found
		if sql_res:
			result['type'] = sql_res[4]
			result['view_id'] = sql_res[3]
			result['arch'] = sql_res[0]

			def _inherit_apply_rec(result, inherit_id):
				# get all views which inherit from (ie modify) this view
				cr.execute('select arch,id from ir_ui_view where inherit_id=%d and model=%s order by priority', (inherit_id, self._name))
				sql_inherit = cr.fetchall()
				for (inherit,id) in sql_inherit:
					result = _inherit_apply(result, inherit)
					result = _inherit_apply_rec(result, id)
				return result

			result['arch'] = _inherit_apply_rec(result['arch'], sql_res[3])

			result['name'] = sql_res[1]
			result['field_parent'] = sql_res[2] or False
		else:
			# otherwise, build some kind of default view
			if view_type == 'form':
				res = self.fields_get(cr, user, context=context)
				xml = '''<?xml version="1.0" encoding="utf-8"?>''' \
				'''<form string="%s">''' % (self._description,)
				for x in res:
					if res[x]['type'] not in ('one2many', 'many2many'):
						xml += '<field name="%s"/>' % (x,)
						if res[x]['type'] == 'text':
							xml += "<newline/>"
				xml += "</form>"
			elif view_type == 'tree':
				xml = '''<?xml version="1.0" encoding="utf-8"?>''' \
				'''<tree string="%s"><field name="%s"/></tree>''' \
				% (self._description, self._rec_name)
			elif view_type == 'calendar':
				xml = self.__get_default_calendar_view()
			else:
				xml = ''
			result['arch'] = xml
			result['name'] = 'default'
			result['field_parent'] = False
			result['view_id'] = 0

		doc = dom.minidom.parseString(result['arch'].encode('utf-8'))
		xarch, xfields = self.__view_look_dom_arch(cr, user, doc, context=context)
		result['arch'] = xarch
		result['fields'] = xfields
		if toolbar:
			def clean(x):
				x = x[2]
				for key in ('report_sxw_content', 'report_rml_content',
						'report_sxw', 'report_rml',
						'report_sxw_content_data', 'report_rml_content_data'):
					if key in x:
						del x[key]
				return x
			ir_values_obj = self.pool.get('ir.values')
			resprint = ir_values_obj.get(cr, user, 'action',
					'client_print_multi', [(self._name, False)], False,
					context)
			resaction = ir_values_obj.get(cr, user, 'action',
					'client_action_multi', [(self._name, False)], False,
					context)

			resrelate = ir_values_obj.get(cr, user, 'action',
					'client_action_relate', [(self._name, False)], False,
					context)
			resprint = map(clean, resprint)
			resaction = map(clean, resaction)
			resaction = filter(lambda x: not x.get('multi',False), resaction)
			resprint = filter(lambda x: not x.get('multi',False), resprint)
			resrelate = map(lambda x:x[2], resrelate)

			for x in resprint+resaction+resrelate:
				x['string'] = x['name']

			result['toolbar'] = {
				'print': resprint,
				'action': resaction,
				'relate': resrelate
			}
		return result

	_view_look_dom_arch=__view_look_dom_arch

	# TODO: ameliorer avec NULL
	def _where_calc(self, cr, user, args, active_test=True, context=None):
		if not context:
			context={}
		args = args[:]
		# if the object has a field named 'active', filter out all inactive
		# records unless they were explicitely asked for
		if 'active' in self._columns and (active_test and context.get('active_test', True)):
			i = 0
			active_found = False
			while i<len(args):
				if args[i][0]=='active':
					active_found = True
				i += 1
			if not active_found:
				args.append(('active', '=', 1))

		i = 0
		tables=['"'+self._table+'"']
		joins=[]
		while i<len(args):
			table=self
			assert args[i][1] in ('like','ilike','not in','inselect','child_of','in','=','<>','<','>','>=','<='), 'Error ! Bad clause operand "%s".' % (args[i][1],)
			if args[i][1] == 'inselect':
				raise except_orm('ValidateError',
						'The clause \'inselect\' can not be used outside the orm!')
			if args[i][0] in self._inherit_fields:
				table=self.pool.get(self._inherit_fields[args[i][0]][0])
				if ('"'+table._table+'"' not in tables):
					tables.append('"'+table._table+'"')
					joins.append(('id', 'join', '%s.%s' % (self._table, self._inherits[table._name]), table))
			fargs = args[i][0].split('.', 1)
			field = table._columns.get(fargs[0],False)
			if not field:
				if args[i][0] == 'id' and args[i][1] == 'child_of':
					ids2 = args[i][2]
					def _rec_get(ids, table, parent):
						if not ids:
							return []
						ids2 = table.search(cr, user, [(parent, 'in', ids)], context=context)
						return ids + _rec_get(ids2, table, parent)
					args[i] = (args[i][0], 'in', ids2 + _rec_get(ids2, table, table._parent_name), table)
				i+=1
				continue
			if len(fargs) > 1:
				if field._type == 'many2one':
					args[i] = (fargs[0], 'in', self.pool.get(field._obj).search(cr, user, [(fargs[1], args[i][1], args[i][2])], context=context))
					i+=1
					continue
				else:
					i+=1
					continue
			if field._properties:
				arg = [args.pop(i)]
				j = i
				while j<len(args):
					if args[j][0]==arg[0][0]:
						arg.append(args.pop(j))
					else:
						j+=1
				if field._fnct_search:
					args.extend(field.search(cr, user, self, arg[0][0], arg))
				if field.store:
					args.extend(arg)
				i+=1
			elif field._type=='one2many':
				field_obj = self.pool.get(field._obj)

				if isinstance(args[i][2], basestring):
					# get the ids of the records of the "distant" resource
					ids2 = [x[0] for x in field_obj.name_search(cr, user, args[i][2], [], args[i][1])]
				else:
					ids2 = args[i][2]
				if not ids2:
					args[i] = ('id','=','0')
				else:
					ids3 = []
					for j in range((len(ids2) / ID_MAX) + (len(ids2) % ID_MAX)):
						sub_ids2 = ids2[ID_MAX * j:ID_MAX * (j + 1)]
						if sub_ids2:
							cr.execute('select "'+field._fields_id+'" ' \
									'from "'+field_obj._table+'" ' \
									'where id in ('+','.join(map(str,sub_ids2))+')')
							ids3.extend([x[0] for x in cr.fetchall()])

					args[i] = ('id', 'in', ids3)
				i+=1

			elif field._type=='many2many':
				#FIXME
				if args[i][1]=='child_of':
					if isinstance(args[i][2], basestring):
						ids2 = [x[0] for x in self.pool.get(field._obj).name_search(cr, user, args[i][2], [], 'like')]
					else:
						ids2 = args[i][2]
					def _rec_get(ids, table, parent):
						if not ids:
							return []
						ids2 = table.search(cr, user, [(parent, 'in', ids)], context=context)
						return ids + _rec_get(ids2, table, parent)
					def _rec_convert(ids):
						if self.pool.get(field._obj)==self:
							return ids
						if not len(ids): return []
						cr.execute('select "'+field._id1+'" from "'+field._rel+'" where "'+field._id2+'" in ('+','.join(map(str,ids))+')')
						ids = [x[0] for x in cr.fetchall()]
						return ids
					args[i] = ('id','in',_rec_convert(ids2+_rec_get(ids2, self.pool.get(field._obj), table._parent_name)))
				else:
					if isinstance(args[i][2], basestring):
						res_ids = [x[0] for x in self.pool.get(field._obj).name_search(cr, user, args[i][2], [], args[i][1])]
					else:
						res_ids = args[i][2]
					if not len(res_ids):
						args[i] = ('id', 'in', [0])
					else:
						cr.execute('select "'+field._id1+'" from "'+field._rel+'" where "'+field._id2+'" in ('+','.join(map(str, res_ids))+')')
						args[i] = ('id', 'in', map(lambda x: x[0], cr.fetchall()))
				i+=1

			elif field._type=='many2one':
				if args[i][1]=='child_of':
					if isinstance(args[i][2], basestring):
						ids2 = [x[0] for x in self.pool.get(field._obj).name_search(cr, user, args[i][2], [], 'like')]
					else:
						ids2 = args[i][2]
					def _rec_get(ids, table, parent):
						if not ids:
							return []
						ids2 = table.search(cr, user, [(parent, 'in', ids)], context=context)
						return ids + _rec_get(ids2, table, parent)
					if field._obj <> table._name:
						args[i] = (args[i][0],'in',ids2+_rec_get(ids2, self.pool.get(field._obj), table._parent_name), table)
					else:
						args[i] = ('id','in',ids2+_rec_get(ids2, table, args[i][0]), table)
				else:
					if isinstance(args[i][2], basestring):
						res_ids = self.pool.get(field._obj).name_search(cr, user, args[i][2], [], args[i][1])
						args[i] = (args[i][0],'in',map(lambda x: x[0], res_ids), table)
					else:
						args[i] += (table,)
				i+=1
			else:
				if field.translate:
					if args[i][1] in ('like', 'ilike'):
						args[i] = (args[i][0], args[i][1], '%%%s%%' % args[i][2])
					query1 = '(SELECT res_id FROM ir_translation ' \
							'WHERE name = %s AND lang = %s ' \
								'AND type = %s ' \
								'AND VALUE ' + args[i][1] + ' %s)'
					query2 = [table._name + ',' + args[i][0],
							context.get('lang', False) or 'en_US',
							'model',
							args[i][2]]
					query1 += ' UNION '
					query1 += '(SELECT id FROM "' + table._table + '" ' \
							'WHERE "' + args[i][0] + '" ' + args[i][1] + ' %s)'
					query2 += [args[i][2]]
					args[i] = ('id', 'inselect', (query1, query2), table)
				else:
					args[i] += (table,)
				i+=1
		args.extend(joins)

		qu1, qu2 = [], []
		for x in args:
			table=self
			if len(x) > 3:
				table=x[3]
			if x[1] == 'inselect':
				qu1.append('(%s.%s in (%s))' % (table._table, x[0], x[2][0]))
				qu2 += x[2][1]
			elif x[1]=='not in':
					if len(x[2])>0:
						todel = []
						for xitem in range(len(x[2])):
							if x[2][xitem]==False and isinstance(x[2][xitem],bool):
								todel.append(xitem)
						for xitem in todel[::-1]:
							del x[2][xitem]
						if x[0]=='id':
							qu1.append('(%s.id not in (%s))' % (table._table, ','.join(['%d'] * len(x[2])),))
						else:
							qu1.append('(%s.%s not in (%s))' % (table._table, x[0], ','.join([table._columns[x[0]]._symbol_set[0]]*len(x[2]))))
						if todel:
							qu1[-1] = '('+qu1[-1]+' or '+x[0]+' is null)'
						qu2+=x[2]
					else:
						qu1.append(' (1=0)')
			elif x[1] != 'in':
#FIXME: this replace all (..., '=', False) values with 'is null' and this is
# not what we want for real boolean fields. The problem is, we can't change it
# easily because we use False everywhere instead of None
# NOTE FAB: we can't use None because it is not accepted by XML-RPC, that's why
# boolean (0-1), None -> False
# Ged> boolean fields are not always = 0 or 1
				if (x[2] is False) and (x[1]=='='):
					qu1.append(x[0]+' is null')
				elif (x[2] is False) and (x[1]=='<>' or x[1]=='!='):
					qu1.append(x[0]+' is not null')
				else:
					if x[0]=='id':
						if x[1]=='join':
							qu1.append('(%s.%s = %s)' % (table._table, x[0], x[2]))
						else:
							qu1.append('(%s.%s %s %%s)' % (table._table, x[0], x[1]))
							qu2.append(x[2])
					else:
						add_null = False
						if x[1] in ('like', 'ilike'):
							if isinstance(x[2], str):
								str_utf8 = x[2]
							elif isinstance(x[2], unicode):
								str_utf8 = x[2].encode('utf-8')
							else:
								str_utf8 = str(x[2])
							qu2.append('%%%s%%' % str_utf8)
							if not str_utf8:
								add_null = True
						else:
							if x[0] in table._columns:
								qu2.append(table._columns[x[0]]._symbol_set[1](x[2]))
						if x[1]=='=like':
							x1 = 'like'
						else:
							x1 = x[1]
						if x[0] in table._columns:
							if x[1] in ('like', 'ilike'):

								qu1.append('(%s.%s %s %s)' % (table._table,
									x[0], x1, '%s'))
							else:
								qu1.append('(%s.%s %s %s)' % (table._table,
									x[0], x1,
									table._columns[x[0]]._symbol_set[0]))
						else:
							qu1.append('(%s.%s %s \'%s\')' % (table._table, x[0], x1, x[2]))

						if add_null:
							qu1[-1] = '('+qu1[-1]+' or '+x[0]+' is null)'
			elif x[1]=='in':
				if len(x[2])>0:
					todel = []
					for xitem in range(len(x[2])):
						if x[2][xitem]==False and isinstance(x[2][xitem],bool):
							todel.append(xitem)
					for xitem in todel[::-1]:
						del x[2][xitem]
					#TODO fix max_stack_depth
					if x[0]=='id':
						qu1.append('(%s.id in (%s))' % (table._table, ','.join(['%d'] * len(x[2])),))
					else:
						qu1.append('(%s.%s in (%s))' % (table._table, x[0], ','.join([table._columns[x[0]]._symbol_set[0]]*len(x[2]))))
					if todel:
						qu1[-1] = '('+qu1[-1]+' or '+x[0]+' is null)'
					qu2+=x[2]
				else:
					qu1.append(' (1=0)')
		return (qu1,qu2,tables)

	def _check_qorder(self, word):
		if not regex_order.match(word):
			raise except_orm('AccessError', 'Bad query.')
		return True

	def search_count(self, cr, user, args, context=None):
		if not context:
			context = {}
		res = self.search(cr, user, args, context=context, count=True)
		if isinstance(res, list):
			return len(res)
		return res

	def search(self, cr, user, args, offset=0, limit=None, order=None,
			context=None, count=False):
		if not context:
			context = {}
		# compute the where, order by, limit and offset clauses
		(qu1,qu2,tables) = self._where_calc(cr, user, args, context=context)

		if len(qu1):
			qu1 = ' where '+string.join(qu1,' and ')
		else:
			qu1 = ''

		if order:
			self._check_qorder(order)
		order_by = order or self._order

		limit_str = limit and ' limit %d' % limit or ''
		offset_str = offset and ' offset %d' % offset or ''


		# construct a clause for the rules :
		d1, d2 = self.pool.get('ir.rule').domain_get(cr, user, self._name)
		if d1:
			qu1 = qu1 and qu1+' and '+d1 or ' where '+d1
			qu2 += d2

		if count:
			cr.execute('select count(%s.id) from ' % self._table +
					','.join(tables) +qu1 + limit_str + offset_str, qu2)
			res = cr.fetchall()
			return res[0][0]
		# execute the "main" query to fetch the ids we were searching for
		cr.execute('select %s.id from ' % self._table + ','.join(tables) +qu1+' order by '+order_by+limit_str+offset_str, qu2)
		res = cr.fetchall()
		return [x[0] for x in res]

	# returns the different values ever entered for one field
	# this is used, for example, in the client when the user hits enter on
	# a char field
	def distinct_field_get(self, cr, uid, field, value, args=None, offset=0, limit=None):
		if not args:
			args=[]
		if field in self._inherit_fields:
			return self.pool.get(self._inherit_fields[field][0]).distinct_field_get(cr, uid,field,value,args,offset,limit)
		else:
			return self._columns[field].search(cr, self, args, field, value, offset, limit, uid)

	def name_get(self, cr, user, ids, context=None):
		if not context:
			context={}
		if not ids:
			return []
		if isinstance(ids, (int, long)):
			ids = [ids]
		return [(r['id'], str(r[self._rec_name])) for r in self.read(cr, user, ids,
			[self._rec_name], context, load='_classic_write')]

	def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=80):
		if not args:
			args=[]
		if not context:
			context={}
		args=args[:]
		if name:
			args += [(self._rec_name,operator,name)]
		ids = self.search(cr, user, args, limit=limit, context=context)
		res = self.name_get(cr, user, ids, context)
		return res

	def copy(self, cr, uid, id, default=None, context=None):
		if not context:
			context={}
		if not default:
			default = {}
		if 'state' not in default:
			if 'state' in self._defaults:
				default['state'] = self._defaults['state'](self, cr, uid, context)
		data = self.read(cr, uid, [id], context=context)[0]
		fields = self.fields_get(cr, uid)
		for f in fields:
			ftype = fields[f]['type']

 			if self._log_access and f in ('create_date', 'create_uid', 'write_date', 'write_uid'):
 				del data[f]

			if f in default:
				data[f] = default[f]
			elif ftype == 'function':
				del data[f]
			elif ftype == 'many2one':
				try:
					data[f] = data[f] and data[f][0]
				except:
					pass
			elif ftype in ('one2many', 'one2one'):
				res = []
				rel = self.pool.get(fields[f]['relation'])
				for rel_id in data[f]:
					# the lines are first duplicated using the wrong (old)
					# parent but then are reassigned to the correct one thanks
					# to the (4, ...)
					res.append((4, rel.copy(cr, uid, rel_id, context=context)))
				data[f] = res
			elif ftype == 'many2many':
				data[f] = [(6, 0, data[f])]
		del data['id']
		for v in self._inherits:
			del data[self._inherits[v]]
		return self.create(cr, uid, data)

	def read_string(self, cr, uid, id, langs, fields=None, context=None):
		if not context:
			context={}
		res = {}
		res2 = {}
		self.pool.get('ir.model.access').check(cr, uid, 'ir.translation', 'read')
		if not fields:
			fields = self._columns.keys() + self._inherit_fields.keys()
		for lang in langs:
			res[lang] = {'code': lang}
			for f in fields:
				if f in self._columns:
					res_trans = self.pool.get('ir.translation')._get_source(cr, uid, self._name+','+f, 'field', lang)
					if res_trans:
						res[lang][f]=res_trans
					else:
						res[lang][f]=self._columns[f].string
		for table in self._inherits:
			cols = intersect(self._inherit_fields.keys(), fields)
			res2 = self.pool.get(table).read_string(cr, uid, id, langs, cols, context)
		for lang in res2:
			if lang in res:
				res[lang]={'code': lang}
			for f in res2[lang]:
				res[lang][f]=res2[lang][f]
		return res

	def write_string(self, cr, uid, id, langs, vals, context=None):
		if not context:
			context={}
		self.pool.get('ir.model.access').check(cr, uid, 'ir.translation', 'write')
		for lang in langs:
			for field in vals:
				if field in self._columns:
					self.pool.get('ir.translation')._set_ids(cr, uid, self._name+','+field, 'field', lang, [0], vals[field])
		for table in self._inherits:
			cols = intersect(self._inherit_fields.keys(), vals)
			if cols:
				self.pool.get(table).write_string(cr, uid, id, langs, vals, context)
		return True

	def check_recursion(self, cr, uid, ids, parent=None):
		if not parent:
			parent = self._parent_name
		ids_parent = ids[:]
		while len(ids_parent):
			ids_parent2 = []
			for i in range((len(ids) / ID_MAX) + ((len(ids) % ID_MAX) and 1 or 0)):
				sub_ids_parent = ids_parent[ID_MAX * i:ID_MAX * (i + 1)]
				cr.execute('SELECT distinct "'+parent+'"'+
					' FROM "'+self._table+'" ' \
					'WHERE id in ('+','.join(map(str, sub_ids_parent))+')')
				ids_parent2.extend(filter(None, map(lambda x: x[0], cr.fetchall())))
			ids_parent = ids_parent2
			for i in ids_parent:
				if i in ids:
					return False
		return True

# vim:noexpandtab:ts=4
