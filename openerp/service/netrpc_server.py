# -*- coding: utf-8 -*-

#
# Copyright P. Christeas <p_christ@hol.gr> 2008,2009
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

#.apidoc title: NET-RPC Server

""" This file contains instance of the net-rpc server

    
"""
import logging
import select
import socket
import sys
import threading
import traceback
import openerp
import openerp.netsvc as netsvc
import openerp.tiny_socket as tiny_socket
import openerp.tools as tools

_logger = logging.getLogger(__name__)

class TinySocketClientThread(threading.Thread):
    def __init__(self, sock, threads):
        spn = sock and sock.getpeername()
        spn = 'netrpc-client-%s:%s' % spn[0:2]
        threading.Thread.__init__(self, name=spn)
        self.sock = sock
        # Only at the server side, use a big timeout: close the
        # clients connection when they're idle for 20min.
        self.sock.settimeout(1200)
        self.threads = threads

    def run(self):
        self.running = True
        try:
            ts = tiny_socket.mysocket(self.sock)
        except Exception:
            self.threads.remove(self)
            self.running = False
            return False

        while self.running:
            try:
                msg = ts.myreceive()
                result = netsvc.dispatch_rpc(msg[0], msg[1], msg[2:])
                ts.mysend(result)
            except socket.timeout:
                #terminate this channel because other endpoint is gone
                break
            except Exception, e:
                try:
                    valid_exception = Exception(netrpc_handle_exception_legacy(e)) 
                    valid_traceback = getattr(e, 'traceback', sys.exc_info())
                    formatted_traceback = "".join(traceback.format_exception(*valid_traceback))
                    _logger.debug("netrpc: communication-level exception", exc_info=True)
                    ts.mysend(valid_exception, exception=True, traceback=formatted_traceback)
                    break
                except Exception, ex:
                    #terminate this channel if we can't properly send back the error
                    _logger.exception("netrpc: cannot deliver exception message to client")
                    break

        netsvc.close_socket(self.sock)
        self.sock = None
        self.threads.remove(self)
        self.running = False
        return True

    def stop(self):
        self.running = False
        
def netrpc_handle_exception_legacy(e):
    if isinstance(e, openerp.osv.osv.except_osv):
        return 'warning -- ' + e.name + '\n\n' + e.value
    if isinstance(e, openerp.exceptions.Warning):
        return 'warning -- Warning\n\n' + str(e)
    if isinstance(e, openerp.exceptions.AccessError):
        return 'warning -- AccessError\n\n' + str(e)
    if isinstance(e, openerp.exceptions.AccessDenied):
        return 'AccessDenied ' + str(e)
    return openerp.tools.exception_to_unicode(e)

class TinySocketServerThread(threading.Thread,netsvc.Server):
    def __init__(self, interface, port, secure=False):
        threading.Thread.__init__(self, name="NetRPCDaemon-%d"%port)
        netsvc.Server.__init__(self)
        self.__port = port
        self.__interface = interface
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.__interface, self.__port))
        self.socket.listen(5)
        self.threads = []
        _logger.info("starting NET-RPC service on %s:%s", interface or '0.0.0.0', port)

    def run(self):
        try:
            self.running = True
            while self.running:
                fd_sets = select.select([self.socket], [], [], self._busywait_timeout)
                if not fd_sets[0]:
                    continue
                (clientsocket, address) = self.socket.accept()
                ct = TinySocketClientThread(clientsocket, self.threads)
                clientsocket = None
                self.threads.append(ct)
                ct.start()
                lt = len(self.threads)
                if (lt > 10) and (lt % 10 == 0):
                     # Not many threads should be serving at the same time, so log
                     # their abuse.
                     _logger.debug("Netrpc: %d threads", len(self.threads))
            self.socket.close()
        except Exception, e:
            _logger.warning("Netrpc: closing because of exception %s" % str(e))
            self.socket.close()
            return False

    def stop(self):
        self.running = False
        for t in self.threads:
            t.stop()
        self._close_socket()

    def stats(self):
        res = "Net-RPC: " + ( (self.running and "running") or  "stopped")
        i = 0
        for t in self.threads:
            i += 1
            res += "\nNet-RPC #%d: %s " % (i, t.name)
            if t.isAlive():
                res += "running"
            else:
                res += "finished"
            if t.sock:
                res += ", socket"
        return res

netrpcd = None

def init_servers():
    global netrpcd
    if tools.config.get('netrpc', False):
        netrpcd = TinySocketServerThread(
            tools.config.get('netrpc_interface', ''), 
            int(tools.config.get('netrpc_port', 8070)))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
