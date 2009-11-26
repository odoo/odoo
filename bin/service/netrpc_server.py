# -*- encoding: utf-8 -*-

#
# Copyright P. Christeas <p_christ@hol.gr> 2008,2009
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

""" This file contains instance of the net-rpc server

    
"""
import netsvc
import threading
import tools
import os
import socket

import tiny_socket
class TinySocketClientThread(threading.Thread, netsvc.OpenERPDispatcher):
    def __init__(self, sock, threads):
        threading.Thread.__init__(self)
        self.sock = sock
        # Only at the server side, use a big timeout: close the
        # clients connection when they're idle for 20min.
        self.sock.settimeout(1200)
        self.threads = threads

    def __del__(self):
        if self.sock:
            try:
                if hasattr(socket, 'SHUT_RDWR'):
                    self.socket.shutdown(socket.SHUT_RDWR)
                else:
                    self.socket.shutdown(2)
            except: pass
            # That should garbage-collect and close it, too
            self.sock = None

    def run(self):
        # import select
        self.running = True
        try:
            ts = tiny_socket.mysocket(self.sock)
        except:
            self.threads.remove(self)
            self.running = False
            return False
        while self.running:
            try:
                msg = ts.myreceive()
            except:
                self.threads.remove(self)
                self.running = False
                return False
            try:
                result = self.dispatch(msg[0], msg[1], msg[2:])
                ts.mysend(result)
            except netsvc.OpenERPDispatcherException, e:
                try:
                    new_e = Exception(tools.exception_to_unicode(e.exception)) # avoid problems of pickeling
                    ts.mysend(new_e, exception=True, traceback=e.traceback)
                except:
                    self.running = False
                    break
            except Exception, e:
                # this code should not be reachable, therefore we warn
                netsvc.Logger().notifyChannel("net-rpc", netsvc.LOG_WARNING, "exception: %" % str(e))
                break

        self.threads.remove(self)
        self.running = False
        return True

    def stop(self):
        self.running = False


class TinySocketServerThread(threading.Thread,netsvc.Server):
    def __init__(self, interface, port, secure=False):
        threading.Thread.__init__(self, name="Net-RPC socket")
        netsvc.Server.__init__(self)
        self.__port = port
        self.__interface = interface
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.__interface, self.__port))
        self.socket.listen(5)
        self.threads = []
        netsvc.Logger().notifyChannel("web-services", netsvc.LOG_INFO, 
                         "starting NET-RPC service at %s port %d" % (interface or '0.0.0.0', port,))

    def run(self):
        # import select
        try:
            self.running = True
            while self.running:
                (clientsocket, address) = self.socket.accept()
                ct = TinySocketClientThread(clientsocket, self.threads)
                clientsocket = None
                self.threads.append(ct)
                ct.start()
                lt = len(self.threads)
                if (lt > 10) and (lt % 10 == 0):
                     # Not many threads should be serving at the same time, so log
                     # their abuse.
                     netsvc.Logger().notifyChannel("web-services", netsvc.LOG_DEBUG,
                        "Netrpc: %d threads" % len(self.threads))
            self.socket.close()
        except Exception, e:
            netsvc.Logger().notifyChannel("web-services", netsvc.LOG_WARNING,
                        "Netrpc: closing because of exception %s" % str(e))
            self.socket.close()
            return False

    def stop(self):
        self.running = False
        for t in self.threads:
            t.stop()
        try:
            if hasattr(socket, 'SHUT_RDWR'):
                self.socket.shutdown(socket.SHUT_RDWR)
            else:
                self.socket.shutdown(2)
            self.socket.close()
        except:
            return False

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
    if tools.config.get_misc('netrpcd','enable', True):
        netrpcd = TinySocketServerThread(tools.config.get_misc('netrpcd','interface', ''), \
            int(tools.config.get_misc('netrpcd','port', tools.config.get('netport', 8070))))
