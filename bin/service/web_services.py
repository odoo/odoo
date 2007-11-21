# -*- encoding: utf-8 -*-
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

import base64, os, string

import netsvc
import pooler, security, ir, tools
import logging

import threading, thread

import time
import base64
import addons

import sql_db

logging.basicConfig()

#TODO: use translation system
def _(str):
	return str

class db(netsvc.Service):
	def __init__(self, name="db"):
		netsvc.Service.__init__(self, name)
		self.joinGroup("web-services")
		self.exportMethod(self.create)
		self.exportMethod(self.get_progress)
		self.exportMethod(self.drop)
		self.exportMethod(self.dump)
		self.exportMethod(self.restore)
		self.exportMethod(self.list)
		self.exportMethod(self.list_lang)
		self.exportMethod(self.change_admin_password)
		self.actions = {}
		self.id = 0
		self.id_protect = threading.Semaphore()

	def create(self, password, db_name, demo, lang):
		security.check_super(password)
		self.id_protect.acquire()
		self.id += 1
		id = self.id
		self.id_protect.release()

		self.actions[id] = {'clean': False}

		db = sql_db.db_connect('template1', serialize=1)
		db.truedb.autocommit()
		cr = db.cursor()
		cr.execute('CREATE DATABASE ' + db_name + ' ENCODING \'unicode\'')
		cr.close()
		class DBInitialize(object):
			def __call__(self, serv, id, db_name, demo, lang):
				try:
					serv.actions[id]['progress'] = 0
					clean = False
					cr = sql_db.db_connect(db_name).cursor()
					tools.init_db(cr)
					cr.commit()
					cr.close()
					pool = pooler.get_pool(db_name, demo,serv.actions[id],
							update_module=True)
					if lang and lang != 'en_US':
						filename = tools.config["root_path"] + "/i18n/" + lang + ".csv"
						tools.trans_load(db_name, filename, lang)
					serv.actions[id]['clean'] = True
					cr = sql_db.db_connect(db_name).cursor()
					cr.execute('select login, password, name ' \
							'from res_users ' \
							'where login <> \'root\' order by login')
					serv.actions[id]['users'] = cr.dictfetchall()
					cr.close()
				except Exception, e:
					serv.actions[id]['clean'] = False
					serv.actions[id]['exception'] = e
					from StringIO import StringIO
					import traceback
					e_str = StringIO()
					traceback.print_exc(file=e_str)
					traceback_str = e_str.getvalue()
					e_str.close()
					serv.actions[id]['traceback'] = traceback_str
					cr.close()
		logger = netsvc.Logger()
		logger.notifyChannel("web-services", netsvc.LOG_INFO,
				'CREATE DB: %s' % (db_name))
		dbi = DBInitialize()
		create_thread = threading.Thread(target=dbi,
				args=(self, id, db_name, demo, lang))
		create_thread.start()
		self.actions[id]['thread'] = create_thread
		return id

	def get_progress(self, password, id):
		security.check_super(password)
		if self.actions[id]['thread'].isAlive():
#			return addons.init_progress[db_name]
			return (min(self.actions[id].get('progress', 0),0.95), [])
		else:
			clean = self.actions[id]['clean']
			if clean:
				users = self.actions[id]['users']
				del self.actions[id]
				return (1.0, users)
			else:
				e = self.actions[id]['exception']
				del self.actions[id]
				raise Exception, e

	def drop(self, password, db_name):
		security.check_super(password)
		pooler.close_db(db_name)
		logger = netsvc.Logger()

		db = sql_db.db_connect('template1', serialize=1)
		db.truedb.autocommit()
		cr = db.cursor()
		try:
			try:
				cr.execute('DROP DATABASE ' + db_name)
			except:
				logger.notifyChannel("web-service", netsvc.LOG_ERROR,
					'DROP DB: %s failed' % (db_name,))
				raise
			else:
				logger.notifyChannel("web-services", netsvc.LOG_INFO,
					'DROP DB: %s' % (db_name))
		finally:
			cr.close()
		return True

	def dump(self, password, db_name):
		security.check_super(password)
		logger = netsvc.Logger()

		if tools.config['db_password']:
			logger.notifyChannel("web-service", netsvc.LOG_ERROR,
					'DUMP DB: %s doesn\'t work with password' % (db_name,))
			raise Exception, "Couldn't dump database with password"

		cmd = ['pg_dump', '--format=c']
		if tools.config['db_user']:
			cmd.append('--username=' + tools.config['db_user'])
		if tools.config['db_host']:
			cmd.append('--host=' + tools.config['db_host'])
		if tools.config['db_port']:
			cmd.append('--port=' + tools.config['db_port'])
		cmd.append(db_name)

		stdin, stdout = tools.exec_pg_command_pipe(*tuple(cmd))
		stdin.close()
		data = stdout.read()
		res = stdout.close()
		if res:
			logger.notifyChannel("web-service", netsvc.LOG_ERROR,
					'DUMP DB: %s failed\n%s' % (db_name, data))
			raise Exception, "Couldn't dump database"
		logger.notifyChannel("web-services", netsvc.LOG_INFO,
				'DUMP DB: %s' % (db_name))
		return base64.encodestring(data)

	def restore(self, password, db_name, data):
		security.check_super(password)
		logger = netsvc.Logger()

		if self.db_exist(db_name):
			logger.notifyChannel("web-service", netsvc.LOG_WARNING,
					'RESTORE DB: %s already exists' % (db_name,))
			raise Exception, "Database already exists"

		if tools.config['db_password']:
			logger.notifyChannel("web-service", netsvc.LOG_ERROR,
					'RESTORE DB: %s doesn\'t work with password' % (db_name,))
			raise Exception, "Couldn't restore database with password"

		db = sql_db.db_connect('template1', serialize=1)
		db.truedb.autocommit()
		cr = db.cursor()
		cr.execute('CREATE DATABASE ' + db_name + ' ENCODING \'unicode\'')
		cr.close()

		cmd = ['pg_restore']
		if tools.config['db_user']:
			cmd.append('--username=' + tools.config['db_user'])
		if tools.config['db_host']:
			cmd.append('--host=' + tools.config['db_host'])
		if tools.config['db_port']:
			cmd.append('--port=' + tools.config['db_port'])
		cmd.append('--dbname=' + db_name)
		args2 = tuple(cmd)

		buf=base64.decodestring(data)
		if os.name == "nt":
			tmpfile = (os.environ['TMP'] or 'C:\\') + os.tmpnam()
			file(tmpfile, 'wb').write(buf)
			args2=list(args2)
			args2.append(' ' + tmpfile)
			args2=tuple(args2)
		stdin, stdout = tools.exec_pg_command_pipe(*args2)
		if not os.name == "nt":
			stdin.write(base64.decodestring(data))
		stdin.close()
		res = stdout.close()
		if res:
			raise Exception, "Couldn't restore database"
		logger.notifyChannel("web-services", netsvc.LOG_INFO,
				'RESTORE DB: %s' % (db_name))
		return True

	def db_exist(self, db_name):
		try:
			db = sql_db.db_connect(db_name)
			db.truedb.close()
			return True
		except:
			return False

	def list(self):
		db = sql_db.db_connect('template1')
		try:
			cr = db.cursor()
			db_user = tools.config["db_user"]
			if not db_user and os.name == 'posix':
				import pwd
				db_user = pwd.getpwuid(os.getuid())[0]
			if not db_user:
				cr.execute("select usename from pg_user where usesysid=(select datdba from pg_database where datname=%s)", (tools.config["db_name"],))
				res = cr.fetchone()
				db_user = res and res[0]
			if db_user:
				cr.execute("select datname from pg_database where datdba=(select usesysid from pg_user where usename=%s) and datname not in ('template0', 'template1', 'postgres')", (db_user,))
			else:
				cr.execute("select datname from pg_database where datname not in('template0', 'template1','postgres')")
			res = [name for (name,) in cr.fetchall()]
			cr.close()
		except:
			res = []
		db.truedb.close()
		return res

	def change_admin_password(self, old_password, new_password):
		security.check_super(old_password)
		tools.config['admin_passwd'] = new_password
		tools.config.save()
		return True
	
	def list_lang(self):
		return tools.scan_languages()
		import glob
		file_list = glob.glob(os.path.join(tools.config['root_path'], 'i18n', '*.csv'))
		def lang_tuple(fname):
			lang_dict=tools.get_languages()
			lang = os.path.basename(fname).split(".")[0]
			return (lang, lang_dict.get(lang, lang))
		return [lang_tuple(fname) for fname in file_list]
db()

class common(netsvc.Service):
	def __init__(self,name="common"):
		netsvc.Service.__init__(self,name)
		self.joinGroup("web-services")
		self.exportMethod(self.ir_get)
		self.exportMethod(self.ir_set)
		self.exportMethod(self.ir_del)
		self.exportMethod(self.about)
		self.exportMethod(self.login)
		self.exportMethod(self.timezone_get)

	def ir_set(self, db, uid, password, keys, args, name, value, replace=True, isobject=False):
		security.check(db, uid, password)
		cr = pooler.get_db(db).cursor()
		res = ir.ir_set(cr,uid, keys, args, name, value, replace, isobject)
		cr.commit()
		cr.close()
		return res

	def ir_del(self, db, uid, password, id):
		security.check(db, uid, password)
		cr = pooler.get_db(db).cursor()
		res = ir.ir_del(cr,uid, id)
		cr.commit()
		cr.close()
		return res

	def ir_get(self, db, uid, password, keys, args=None, meta=None, context=None):
		if not args:
			args=[]
		if not context:
			context={}
		security.check(db, uid, password)
		cr = pooler.get_db(db).cursor()
		res = ir.ir_get(cr,uid, keys, args, meta, context)
		cr.commit()
		cr.close()
		return res

	def login(self, db, login, password):
		res = security.login(db, login, password)
		logger = netsvc.Logger()
		msg = res and 'successful login' or 'bad login or password'
		logger.notifyChannel("web-service", netsvc.LOG_INFO, "%s from '%s' using database '%s'" % (msg, login, db))
		return res or False

	def about(self):
		return tools.version_string + _('''

Tiny ERP is an ERP+CRM program for small and medium businesses.

The whole source code is distributed under the terms of the
GNU Public Licence.

(c) 2003-TODAY, Fabien Pinckaers - Tiny sprl''')

	def timezone_get(self, db, login, password):
		return time.tzname[0]
common()

class objects_proxy(netsvc.Service):
	def __init__(self, name="object"):
		netsvc.Service.__init__(self,name)
		self.joinGroup('web-services')
		self.exportMethod(self.execute)
		self.exportMethod(self.exec_workflow)
		self.exportMethod(self.obj_list)
		
	def exec_workflow(self, db, uid, passwd, object, method, id):
		security.check(db, uid, passwd)
		service = netsvc.LocalService("object_proxy")
		res = service.exec_workflow(db, uid, object, method, id)
		return res
		
	def execute(self, db, uid, passwd, object, method, *args):
		security.check(db, uid, passwd)
		service = netsvc.LocalService("object_proxy")
		res = service.execute(db, uid, object, method, *args)
		return res

	def obj_list(self, db, uid, passwd):
		security.check(db, uid, passwd)
		service = netsvc.LocalService("object_proxy")
		res = service.obj_list()
		return res
objects_proxy()


#
# Wizard ID: 1
#    - None = end of wizard
#
# Wizard Type: 'form'
#    - form
#    - print
#
# Wizard datas: {}
# TODO: change local request to OSE request/reply pattern
#
class wizard(netsvc.Service):
	def __init__(self, name='wizard'):
		netsvc.Service.__init__(self,name)
		self.joinGroup('web-services')
		self.exportMethod(self.execute)
		self.exportMethod(self.create)
		self.id = 0
		self.wiz_datas = {}
		self.wiz_name = {}
		self.wiz_uid = {}

	def _execute(self, db, uid, wiz_id, datas, action, context):
		self.wiz_datas[wiz_id].update(datas)
		wiz = netsvc.LocalService('wizard.'+self.wiz_name[wiz_id])
		return wiz.execute(db, uid, self.wiz_datas[wiz_id], action, context)

	def create(self, db, uid, passwd, wiz_name, datas=None):
		if not datas:
			datas={}
		security.check(db, uid, passwd)
#FIXME: this is not thread-safe
		self.id += 1
		self.wiz_datas[self.id] = {}
		self.wiz_name[self.id] = wiz_name
		self.wiz_uid[self.id] = uid
		return self.id

	def execute(self, db, uid, passwd, wiz_id, datas, action='init', context=None):
		if not context:
			context={}
		security.check(db, uid, passwd)

		if wiz_id in self.wiz_uid:
			if self.wiz_uid[wiz_id] == uid:
				return self._execute(db, uid, wiz_id, datas, action, context)
			else:
				raise Exception, 'AccessDenied'
		else:
			raise Exception, 'WizardNotFound'
wizard()

#
# TODO: set a maximum report number per user to avoid DOS attacks
#
# Report state:
#     False -> True
#
class report_spool(netsvc.Service):
	def __init__(self, name='report'):
		netsvc.Service.__init__(self, name)
		self.joinGroup('web-services')
		self.exportMethod(self.report)
		self.exportMethod(self.report_get)
		self._reports = {}
		self.id = 0
		self.id_protect = threading.Semaphore()

	def report(self, db, uid, passwd, object, ids, datas=None, context=None):
		if not datas:
			datas={}
		if not context:
			context={}
		security.check(db, uid, passwd)
		
		self.id_protect.acquire()
		self.id += 1
		id = self.id
		self.id_protect.release()

		self._reports[id] = {'uid': uid, 'result': False, 'state': False}

		def go(id, uid, ids, datas, context):
			cr = pooler.get_db(db).cursor()
			obj = netsvc.LocalService('report.'+object)
			(result, format) = obj.create(cr, uid, ids, datas, context)
			cr.close()
			self._reports[id]['result'] = result
			self._reports[id]['format'] = format
			self._reports[id]['state'] = True
			return True

		thread.start_new_thread(go, (id, uid, ids, datas, context))
		return id

	def _check_report(self, report_id):
		result = self._reports[report_id]
		res = {'state': result['state']}
		if res['state']:
			if tools.config['reportgz']:
				import zlib
				res2 = zlib.compress(result['result'])
				res['code'] = 'zlib'
			else:
				#CHECKME: why is this needed???
				if isinstance(result['result'], unicode):
					res2 = result['result'].encode('latin1', 'replace')
				else:
					res2 = result['result']
			if res2:
				res['result'] = base64.encodestring(res2)
			res['format'] = result['format']
			del self._reports[report_id]
		return res

	def report_get(self, db, uid, passwd, report_id):
		security.check(db, uid, passwd)

		if report_id in self._reports:
			if self._reports[report_id]['uid'] == uid:
				return self._check_report(report_id)
			else:
				raise Exception, 'AccessDenied'
		else:
			raise Exception, 'ReportNotFound'

report_spool()

# vim:noexpandtab
