#!/usr/bin/python

##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be)
#
# $Id: tinyerp-server.py 1308 2005-09-08 18:02:01Z pinky $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contact a Free Software
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

"""
Tiny ERP - Server
Tiny ERP is an ERP+CRM program for small and medium businesses.

The whole source code is distributed under the terms of the
GNU Public Licence.

(c) 2003-TODAY, Fabien Pinckaers - Tiny sprl
"""
import release
__author__ = release.author
__version__ = release.version

import __builtin__
__builtin__.__dict__['tinyerp_version'] = __version__
__builtin__.__dict__['tinyerp_version_string'] = "Tiny ERP Server " + __version__



#----------------------------------------------------------
# python imports
#----------------------------------------------------------
import sys,os,signal

#----------------------------------------------------------
# ubuntu 8.04 has obsoleted `pyxml` package and installs here.
# the path needs to be updated before any `import xml`
#----------------------------------------------------------
_oldxml = '/usr/lib/python%s/site-packages/oldxml' % sys.version[:3]
if os.path.exists(_oldxml):
    sys.path.append(_oldxml)

#----------------------------------------------------------
# get logger
#----------------------------------------------------------
import netsvc

netsvc.init_logger()

logger = netsvc.Logger()

#-----------------------------------------------------------------------
# import the tools module so that the commandline parameters are parsed
#-----------------------------------------------------------------------
import tools
import time

if sys.platform=='win32':
	import mx.DateTime
	mx.DateTime.strptime = lambda x,y: mx.DateTime.mktime(time.strptime(x, y))

#os.chdir(tools.file_path_root)

#----------------------------------------------------------
# init net service
#----------------------------------------------------------
logger.notifyChannel("objects", netsvc.LOG_INFO, 'initialising distributed objects services')

dispatcher = netsvc.Dispatcher()
dispatcher.monitor(signal.SIGINT)

#---------------------------------------------------------------
# connect to the database and initialize it with base if needed
#---------------------------------------------------------------
logger.notifyChannel("init", netsvc.LOG_INFO, 'connecting to database')

import psycopg
import pooler

# try to connect to the database
try:
#	pooler.init()
	pass
except psycopg.OperationalError, err:
	logger.notifyChannel("init", netsvc.LOG_ERROR, "could not connect to database '%s'!" % (tools.config["db_name"],))

	msg = str(err).replace("FATAL:","").strip()
	db_msg = "database \"%s\" does not exist" % (tools.config["db_name"],)
	
	# Note: this is ugly but since psycopg only uses one exception for all errors
	# I don't think it's possible to do differently
	if msg == db_msg:
		print """
    this database does not exist

You need to create it using the command:

    createdb --encoding=UNICODE '%s'

When you run tinyerp-server for the first time it will initialise the
database. You may force this behaviour at a later time by using the command:

    ./tinyerp-server --init=all

Two accounts will be created by default:
    1. login: admin      password : admin
    2. login: demo       password : demo

""" % (tools.config["db_name"])
	else:
		print "\n    "+msg+"\n"
	sys.exit(1)

db_name = tools.config["db_name"]

# test whether it is needed to initialize the db (the db is empty)
try:
	cr = pooler.get_db_only(db_name).cursor()
except psycopg.OperationalError:
	logger.notifyChannel("init", netsvc.LOG_INFO, "could not connect to database '%s'!" % db_name,)
	cr = None
if cr:
	cr.execute("SELECT relname FROM pg_class WHERE relkind='r' AND relname='perm'")
	if len(cr.fetchall())==0:
#if False:
		logger.notifyChannel("init", netsvc.LOG_INFO, "init db")
		tools.init_db(cr)
		# in that case, force --init=all
		tools.config["init"]["all"] = 1
		tools.config['update']['all'] = 1
		if not tools.config['without_demo']:
			tools.config["demo"]['all'] = 1
	cr.close()

#----------------------------------------------------------
# launch modules install/upgrade/removes if needed
#----------------------------------------------------------
if tools.config['upgrade']:
	print 'Upgrading new modules...'
	import tools.upgrade
	(toinit, toupdate) = tools.upgrade.upgrade()
	for m in toinit:
		tools.config['init'][m] = 1
	for m in toupdate:
		tools.config['update'][m] = 1

#----------------------------------------------------------
# import basic modules 
#----------------------------------------------------------
import osv, workflow, report, service

#----------------------------------------------------------
# import addons
#----------------------------------------------------------
import addons

addons.register_classes()
if tools.config['init'] or tools.config['update']:
	pooler.get_db_and_pool(tools.config['db_name'], update_module=True)

#----------------------------------------------------------
# translation stuff
#----------------------------------------------------------
if tools.config["translate_out"]:
	import csv

	logger.notifyChannel("init", netsvc.LOG_INFO, 'writing translation file for language %s to %s' % (tools.config["language"], tools.config["translate_out"]))
	trans=tools.trans_generate(tools.config["language"], tools.config["translate_modules"])
	writer=csv.writer(file(tools.config["translate_out"], "w"), 'TINY')
	for row in trans:
		writer.writerow(row)
	del trans
	logger.notifyChannel("init", netsvc.LOG_INFO, 'translation file written succesfully')
	sys.exit(0)

if tools.config["translate_in"]:
	tools.trans_load(tools.config["db_name"], tools.config["translate_in"], tools.config["language"])
	sys.exit(0)

#----------------------------------------------------------------------------------
# if we don't want the server to continue to run after initialization, we quit here
#----------------------------------------------------------------------------------
if tools.config["stop_after_init"]:
    sys.exit(0)


#----------------------------------------------------------
# Launch Server
#----------------------------------------------------------

if tools.config['xmlrpc']:
	try:
		port = int(tools.config["port"])
	except Exception:
		logger.notifyChannel("init", netsvc.LOG_ERROR, "invalid port '%s'!" % (tools.config["port"],))
		sys.exit(1)
	interface = tools.config["interface"]
	secure = tools.config["secure"]
	
	httpd = netsvc.HttpDaemon(interface,port, secure)
	
	if tools.config["xmlrpc"]:
		xml_gw = netsvc.xmlrpc.RpcGateway('web-services')
		httpd.attach("/xmlrpc", xml_gw )
		logger.notifyChannel("web-services", netsvc.LOG_INFO,
				"starting XML-RPC" + \
						(tools.config['secure'] and ' Secure' or '') + \
						" services, port " + str(port))

	#
	#if tools.config["soap"]:
	#	soap_gw = netsvc.xmlrpc.RpcGateway('web-services')
	#	httpd.attach("/soap", soap_gw )
	#	logger.notifyChannel("web-services", netsvc.LOG_INFO, 'starting SOAP services, port '+str(port))
	#

if tools.config['netrpc']:
	try:
		netport = int(tools.config["netport"])
	except Exception:
		logger.notifyChannel("init", netsvc.LOG_ERROR, "invalid port '%s'!" % (tools.config["netport"],))
		sys.exit(1)
	netinterface = tools.config["netinterface"]
	
	tinySocket = netsvc.TinySocketServerThread(netinterface, netport, False)
	logger.notifyChannel("web-services", netsvc.LOG_INFO, "starting netrpc service, port "+str(netport))

def handler(signum, frame):
	from tools import config
	if tools.config['netrpc']:
		tinySocket.stop()
	if tools.config['xmlrpc']:
		httpd.stop()
	netsvc.Agent.quit()
	if config['pidfile']:
		os.unlink(config['pidfile'])
	sys.exit(0)

from tools import config
if config['pidfile']:
	fd=open(config['pidfile'], 'w')
	pidtext="%d" % (os.getpid())
	fd.write(pidtext)
	fd.close()

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

logger.notifyChannel("web-services", netsvc.LOG_INFO, 'the server is running, waiting for connections...')
if tools.config['netrpc']:
	tinySocket.start()
if tools.config['xmlrpc']:
	httpd.start()
#dispatcher.run()

while True:
	time.sleep(1)
