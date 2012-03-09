# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

import logging
import threading
import time

import http_server
import netrpc_server
import web_services
import websrv_lib

import openerp.cron
import openerp.modules
import openerp.netsvc
import openerp.osv
import openerp.tools
import openerp.wsgi

#.apidoc title: RPC Services

""" Classes of this module implement the network protocols that the
    OpenERP server uses to communicate with remote clients.

    Some classes are mostly utilities, whose API need not be visible to
    the average user/developer. Study them only if you are about to
    implement an extension to the network protocols, or need to debug some
    low-level behavior of the wire.
"""

_logger = logging.getLogger(__name__)

# TODO block until the server is really up, accepting connections
# TODO be idemptotent (as long as stop_service was not called).
def start_services():
    """ Start all services.

    Services include the different servers and cron threads.

    """
    # Instantiate local services (this is a legacy design).
    openerp.osv.osv.start_object_proxy()
    # Export (for RPC) services.
    web_services.start_web_services()

    # Initialize the HTTP stack.
    #http_server.init_servers()
    #http_server.init_static_http()
    netrpc_server.init_servers()

    # Start the main cron thread.
    openerp.cron.start_master_thread()

    # Start the top-level servers threads (normally HTTP, HTTPS, and NETRPC).
    openerp.netsvc.Server.startAll()

    # Start the WSGI server.
    openerp.wsgi.core.start_server()


def stop_services():
    """ Stop all services. """
    # stop scheduling new jobs; we will have to wait for the jobs to complete below
    openerp.cron.cancel_all()

    openerp.netsvc.Server.quitAll()
    openerp.wsgi.core.stop_server()
    config = openerp.tools.config
    _logger.info("Initiating shutdown")
    _logger.info("Hit CTRL-C again or send a second signal to force the shutdown.")
    logging.shutdown()

    # Manually join() all threads before calling sys.exit() to allow a second signal
    # to trigger _force_quit() in case some non-daemon threads won't exit cleanly.
    # threading.Thread.join() should not mask signals (at least in python 2.5).
    for thread in threading.enumerate():
        if thread != threading.currentThread() and not thread.isDaemon():
            while thread.isAlive():
                # Need a busyloop here as thread.join() masks signals
                # and would prevent the forced shutdown.
                thread.join(0.05)
                time.sleep(0.05)

    openerp.modules.registry.RegistryManager.delete_all()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

