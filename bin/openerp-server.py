#!/usr/bin/python
# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

"""
OpenERP - Server
OpenERP is an ERP+CRM program for small and medium businesses.

The whole source code is distributed under the terms of the
GNU Public Licence.

(c) 2003-TODAY, Fabien Pinckaers - Tiny sprl
"""

#----------------------------------------------------------
# python imports
#----------------------------------------------------------
import sys, os, signal,pwd
#----------------------------------------------------------
# ubuntu 8.04 has obsoleted `pyxml` package and installs here.
# the path needs to be updated before any `import xml`
# TODO: remove PyXML dependencies, use lxml instead.
#----------------------------------------------------------
_oldxml = '/usr/lib/python%s/site-packages/oldxml' % sys.version[:3]
if os.path.exists(_oldxml):
    sys.path.append(_oldxml)


import release
__author__ = release.author
__version__ = release.version

# We DON't log this using the standard logger, because we might mess
# with the logfile's permissions. Just do a quick exit here.
if pwd.getpwuid(os.getuid())[0] == 'root' :
	sys.stderr.write("Attempted to run OpenERP server as root. This is not good, aborting.\n")
        sys.exit(1)

#----------------------------------------------------------
# get logger
#----------------------------------------------------------
import netsvc
logger = netsvc.Logger()

#-----------------------------------------------------------------------
# import the tools module so that the commandline parameters are parsed
#-----------------------------------------------------------------------
import tools

logger.notifyChannel("server", netsvc.LOG_INFO, "version - %s" % release.version )
for name, value in [('addons_path', tools.config['addons_path']),
                    ('database hostname', tools.config['db_host'] or 'localhost')]:
    logger.notifyChannel("server", netsvc.LOG_INFO, "%s - %s" % ( name, value ))

import time

if sys.platform == 'win32':
    import mx.DateTime
    mx.DateTime.strptime = lambda x, y: mx.DateTime.mktime(time.strptime(x, y))

#----------------------------------------------------------
# init net service
#----------------------------------------------------------
logger.notifyChannel("objects", netsvc.LOG_INFO, 'initialising distributed objects services')

dispatcher = netsvc.Dispatcher()
dispatcher.monitor(signal.SIGINT)

#---------------------------------------------------------------
# connect to the database and initialize it with base if needed
#---------------------------------------------------------------
import pooler

#----------------------------------------------------------
# launch modules install/upgrade/removes if needed
#----------------------------------------------------------
if tools.config['upgrade']:
    logger.notifyChannel('init', netsvc.LOG_INFO, 'Upgrading new modules...')
    import tools.upgrade
    (toinit, toupdate) = tools.upgrade.upgrade()
    for m in toinit:
        tools.config['init'][m] = 1
    for m in toupdate:
        tools.config['update'][m] = 1

#----------------------------------------------------------
# import basic modules
#----------------------------------------------------------
import osv
import workflow
import report
import service

#----------------------------------------------------------
# import addons
#----------------------------------------------------------

import addons

#----------------------------------------------------------
# Load and update databases if requested
#----------------------------------------------------------

if tools.config['db_name']:
    for db in tools.config['db_name'].split(','):
        pooler.get_db_and_pool(db, update_module=tools.config['init'] or tools.config['update'])

#----------------------------------------------------------
# translation stuff
#----------------------------------------------------------
if tools.config["translate_out"]:
    import csv

    if tools.config["language"]:
        msg = "language %s" % (tools.config["language"],)
    else:
        msg = "new language"
    logger.notifyChannel("init", netsvc.LOG_INFO, 'writing translation file for %s to %s' % (msg, tools.config["translate_out"]))

    fileformat = os.path.splitext(tools.config["translate_out"])[-1][1:].lower()
    buf = file(tools.config["translate_out"], "w")
    tools.trans_export(tools.config["language"], tools.config["translate_modules"], buf, fileformat)
    buf.close()

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

    httpd = netsvc.HttpDaemon(interface, port, secure)

    if tools.config["xmlrpc"]:
        xml_gw = netsvc.xmlrpc.RpcGateway('web-services')
        httpd.attach("/xmlrpc", xml_gw)
        logger.notifyChannel("web-services", netsvc.LOG_INFO, "starting XML-RPC%s services, port %s" % ((tools.config['secure'] and ' Secure' or ''), port))

#
#if tools.config["soap"]:
#   soap_gw = netsvc.xmlrpc.RpcGateway('web-services')
#   httpd.attach("/soap", soap_gw )
#   logger.notifyChannel("web-services", netsvc.LOG_INFO, 'starting SOAP services, port '+str(port))
#

if tools.config['netrpc']:
    try:
        netport = int(tools.config["netport"])
    except Exception:
        logger.notifyChannel("init", netsvc.LOG_ERROR, "invalid port '%s'!" % (tools.config["netport"],))
        sys.exit(1)
    netinterface = tools.config["netinterface"]

    tinySocket = netsvc.TinySocketServerThread(netinterface, netport, False)
    logger.notifyChannel("web-services", netsvc.LOG_INFO, "starting NET-RPC service, port "+str(netport))


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
    fd = open(config['pidfile'], 'w')
    pidtext = "%d" % (os.getpid())
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

