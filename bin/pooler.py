##############################################################################
#
# Copyright (c) 2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

import sql_db
import osv.osv
import tools
import addons

db_dic = {}
pool_dic = {}

def get_db_and_pool(db_name, force_demo=False, status={}, update_module=False):
	if db_name in db_dic:
		db = db_dic[db_name]
	else:
		print 'Pooler Connecting to', db_name
		db = sql_db.db_connect(db_name)
		db_dic[db_name] = db
	
	if db_name in pool_dic:
		pool = pool_dic[db_name]
	else:
		pool = osv.osv.osv_pool()
		pool_dic[db_name] = pool
		addons.load_modules(db, force_demo, status, update_module)

		import report
		report.interface.register_all(db)

#		pool.get('ir.cron')._poolJobs(db.dbname)
	return db, pool

def restart_pool(db_name, force_demo=False, update_module=False):
#	del db_dic[db_name]
	del pool_dic[db_name]
	return get_db_and_pool(db_name, force_demo, update_module=update_module)

def close_db(db_name):
	if db_name in db_dic:
		db_dic[db_name].truedb.close()
		del db_dic[db_name]
	if db_name in pool_dic:
		del pool_dic[db_name]

def get_db_only(db_name):
	if db_name in db_dic:
		db = db_dic[db_name]
	else:
		db = sql_db.db_connect(db_name)
		db_dic[db_name] = db
	return db

def get_db(db_name):
#	print "get_db", db_name
	return get_db_and_pool(db_name)[0]

def get_pool(db_name, force_demo=False, status={}, update_module=False):
#	print "get_pool", db_name
	pool = get_db_and_pool(db_name, force_demo, status, update_module)[1]
#	addons.load_modules(db_name, False)
#	if not pool.obj_list():
#		pool.instanciate()
#	print "pool", pool
	return pool
#	return get_db_and_pool(db_name)[1]

def init():
	global db
#	db = get_db_only(tools.config['db_name'])
	sql_db.init()

