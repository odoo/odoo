##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: pooler.py 1310 2005-09-08 20:40:15Z pinky $
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

import psycopg
import tools
import sys,os

#try:
#	import decimal
#except ImportError:
#	from tools import decimal


import re

from mx import DateTime as mdt
re_from = re.compile('.* from "?([a-zA-Z_0-9]+)"? .*$');
re_into = re.compile('.* into "?([a-zA-Z_0-9]+)"? .*$');

class fake_cursor:
	nbr = 0
	_tables = {}
	sql_from_log = {}
	sql_into_log = {}
	sql_log = False
	count = 0

	def __init__(self, db, con, dbname):
		self.db = db
		self.obj = db.cursor()
		self.con = con
		self.dbname = dbname

	def execute(self,*args):
		#if not fake_cursor.nbr % 1:
		#	print 'sql: ',fake_cursor.nbr, args
		res = re.match('^select.* from ([a-zA-Z_]+) .*$', args[0], re.I)
		if res:
			fake_cursor._tables.setdefault(res.group(1), 0)
			fake_cursor._tables[res.group(1)] += 1

		#else:
		#	if len(args)>1:
		#		print 'sql: ',fake_cursor.nbr, args[0], args[1]
		#	else:
		#		print 'sql: ',fake_cursor.nbr, args[0]

		if not fake_cursor.nbr % 500:
			ct = []
			for t,c in fake_cursor._tables.items():
				ct.append([c,t])
			ct.sort()
			ct.reverse()
			print 'After %d queries' % (fake_cursor.nbr,)
			for line in ct[:50]:
				print '    %s: %d' % (line[1], line[0])

		#if len(args)>1:
		#	print 'sql: ',fake_cursor.nbr, args[0], args[1]
		#else:
		#	print 'sql: ',fake_cursor.nbr, args[0]

		fake_cursor.nbr += 1
		return self.obj.execute(*args)

	def execute(self, sql, params=None):
		if not params:
			params=()
		def base_string(s):
			if isinstance(s, unicode):
				return s.encode('utf-8')
			return s
		p=map(base_string, params)
		if isinstance(sql, unicode):
			sql = sql.encode('utf-8')
		if self.sql_log:
			now = mdt.now()
		if p:
			res = self.obj.execute(sql, p)
		else:
			res = self.obj.execute(sql)
		if self.sql_log:
			self.count+=1
			res_from = re_from.match(sql.lower())
			if res_from:
				self.sql_from_log.setdefault(res_from.group(1), [0, 0])
				self.sql_from_log[res_from.group(1)][0] += 1
				self.sql_from_log[res_from.group(1)][1] += mdt.now() - now
			res_into = re_into.match(sql.lower())
			if res_into:
				self.sql_into_log.setdefault(res_into.group(1), [0, 0])
				self.sql_into_log[res_into.group(1)][0] += 1
				self.sql_into_log[res_into.group(1)][1] += mdt.now() - now
		return res

	def print_log(self, type='from'):
		print "SQL LOG %s:" % (type,)
		if type == 'from':
			logs = self.sql_from_log.items()
		else:
			logs = self.sql_into_log.items()
		logs.sort(lambda x, y: cmp(x[1][1], y[1][1]))
		sum=0
		for r in logs:
			print "table:", r[0], ":", str(r[1][1]), "/", r[1][0]
			sum+= r[1][1]
		print "SUM:%s/%d"% (sum, self.count)

	def close(self):
		if self.sql_log:
			self.print_log('from')
			self.print_log('into')
		self.obj.close()

		# This force the cursor to be freed, and thus, available again. It is 
		# important because otherwise we can overload the server very easily 
		# because of a cursor shortage (because cursors are not garbage
		# collected as fast as they should). The problem is probably due in 
		# part because browse records keep a reference to the cursor.
		del self.obj

	def __getattr__(self, name):
		return getattr(self.obj, name)

class fakedb:
	def __init__(self, truedb, dbname):
		self.truedb = truedb
		self.dbname = dbname
		
	def cursor(self):
		return fake_cursor(self.truedb, {}, self.dbname)

def decimalize(symb):
	if symb is None: return None
	if isinstance(symb, float):
		return decimal.Decimal('%f' % symb)
	return decimal.Decimal(symb)

def db_connect(db_name):
	host = tools.config['db_host'] and "host=%s" % tools.config['db_host'] or ''
	port = tools.config['db_port'] and "port=%s" % tools.config['db_port'] or ''
	name = "dbname=%s" % db_name
	user = tools.config['db_user'] and "user=%s" % tools.config['db_user'] or ''
	password = tools.config['db_password'] and "password=%s" % tools.config['db_password'] or ''
	maxconn = int(tools.config['db_maxconn']) or 64
	tdb = psycopg.connect('%s %s %s %s %s' % (host, port, name, user, password), serialize=0, maxconn=maxconn)
	fdb = fakedb(tdb, db_name)
	return fdb

def init():
	#define DATEOID 1082, define TIMESTAMPOID 1114 see pgtypes.h
	psycopg.register_type(psycopg.new_type((1082,), "date", lambda x:x))
	psycopg.register_type(psycopg.new_type((1083,), "time", lambda x:x))
	psycopg.register_type(psycopg.new_type((1114,), "datetime", lambda x:x))
	#psycopg.register_type(psycopg.new_type((700, 701, 1700), 'decimal', decimalize))

psycopg.register_type(psycopg.new_type((1082,), "date", lambda x:x))
psycopg.register_type(psycopg.new_type((1083,), "time", lambda x:x))
psycopg.register_type(psycopg.new_type((1114,), "datetime", lambda x:x))

