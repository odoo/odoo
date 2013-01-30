# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2012 OpenERP SA (<http://www.openerp.com>)
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
import os
import signal
import subprocess
import sys
import threading
import time

import cron
import netrpc_server
import web_services
import web_services
import wsgi_server

import openerp.modules
import openerp.netsvc
import openerp.osv
from openerp.release import nt_service_name
import openerp.tools

#.apidoc title: RPC Services

""" Classes of this module implement the network protocols that the
    OpenERP server uses to communicate with remote clients.

    Some classes are mostly utilities, whose API need not be visible to
    the average user/developer. Study them only if you are about to
    implement an extension to the network protocols, or need to debug some
    low-level behavior of the wire.
"""

_logger = logging.getLogger(__name__)

def load_server_wide_modules():
    for m in openerp.conf.server_wide_modules:
        try:
            openerp.modules.module.load_openerp_module(m)
        except Exception:
            msg = ''
            if m == 'web':
                msg = """
The `web` module is provided by the addons found in the `openerp-web` project.
Maybe you forgot to add those addons in your addons_path configuration."""
            _logger.exception('Failed to load server-wide module `%s`.%s', m, msg)

start_internal_done = False
main_thread_id = threading.currentThread().ident

def start_internal():
    global start_internal_done
    if start_internal_done:
        return
    openerp.netsvc.init_logger()
    openerp.modules.loading.open_openerp_namespace()

    # Instantiate local services (this is a legacy design).
    openerp.osv.osv.start_object_proxy()
    # Export (for RPC) services.
    web_services.start_service()

    load_server_wide_modules()
    start_internal_done = True

def start_services():
    """ Start all services including http, netrpc and cron """
    start_internal()
    # Initialize the NETRPC server.
    netrpc_server.start_service()
    # Start the WSGI server.
    wsgi_server.start_service()
    # Start the main cron thread.
    cron.start_service()

def stop_services():
    """ Stop all services. """
    # stop services
    cron.stop_service()
    netrpc_server.stop_service()
    wsgi_server.stop_service()

    _logger.info("Initiating shutdown")
    _logger.info("Hit CTRL-C again or send a second signal to force the shutdown.")

    # Manually join() all threads before calling sys.exit() to allow a second signal
    # to trigger _force_quit() in case some non-daemon threads won't exit cleanly.
    # threading.Thread.join() should not mask signals (at least in python 2.5).
    me = threading.currentThread()
    _logger.debug('current thread: %r', me)
    for thread in threading.enumerate():
        _logger.debug('process %r (%r)', thread, thread.isDaemon())
        if thread != me and not thread.isDaemon() and thread.ident != main_thread_id:
            while thread.isAlive():
                _logger.debug('join and sleep')
                # Need a busyloop here as thread.join() masks signals
                # and would prevent the forced shutdown.
                thread.join(0.05)
                time.sleep(0.05)

    _logger.debug('--')
    openerp.modules.registry.RegistryManager.delete_all()
    logging.shutdown()

def start_services_workers():
    import openerp.service.workers
    openerp.multi_process = True
    openerp.service.workers.Multicorn(openerp.service.wsgi_server.application).run()

def _reexec():
    """reexecute openerp-server process with (nearly) the same arguments"""
    if openerp.tools.osutil.is_running_as_nt_service():
        subprocess.call('net stop {0} && net start {0}'.format(nt_service_name), shell=True)
    exe = os.path.basename(sys.executable)
    strip_args = ['-d', '-u']
    a = sys.argv[:]
    args = [x for i, x in enumerate(a) if x not in strip_args and a[max(i - 1, 0)] not in strip_args]
    if not args or args[0] != exe:
        args.insert(0, exe)
    os.execv(sys.executable, args)

def restart_server():
    if openerp.multi_process:
        raise NotImplementedError("Multicorn is not supported (but gunicorn was)")
        pid = openerp.wsgi.core.arbiter_pid
        os.kill(pid, signal.SIGHUP)
    else:
        if os.name == 'nt':
            def reborn():
                stop_services()
                _reexec()

            # run in a thread to let the current thread return response to the caller.
            threading.Thread(target=reborn).start()
        else:
            openerp.phoenix = True
            os.kill(os.getpid(), signal.SIGINT)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
