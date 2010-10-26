# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution   
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

import threading
import ftpserver
import authorizer
import abstracted_fs
import netsvc

from tools import config

DEFAULT_HOST = '0.0.0.0' # all interfaces
HOST = config.get('ftp_server_host')
PORT = int(config.get('ftp_server_port', 8021))
PASSIVE_PORTS = None
pps = config.get('ftp_server_passive_ports', '').split(':')
if len(pps) == 2:
    PASSIVE_PORTS = int(pps[0]), int(pps[1])

class ftp_server(threading.Thread):
    def log(self, level, message):
        logger = netsvc.Logger()
        logger.notifyChannel('FTP', level, message)

    def detect_ip_addr(self):
        def _detect_ip_addr():
            from array import array
            import socket
            from struct import pack, unpack

            try:
                import fcntl
            except ImportError:
                fcntl = None

            if not fcntl: # not UNIX:
                hostname = socket.gethostname()
                ip_addr = socket.gethostbyname(hostname)
            else: # UNIX:
                # get all interfaces:
                nbytes = 128 * 32
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                names = array('B', '\0' * nbytes)
                outbytes = unpack('iL', fcntl.ioctl( s.fileno(), 0x8912, pack('iL', nbytes, names.buffer_info()[0])))[0]
                namestr = names.tostring()
                ifaces = [namestr[i:i+32].split('\0', 1)[0] for i in range(0, outbytes, 32)]

                for ifname in [iface for iface in ifaces if iface != 'lo']:
                    ip_addr = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, pack('256s', ifname[:15]))[20:24])
                    break
            return ip_addr

        try:
            ip_addr = _detect_ip_addr()
        except:
            ip_addr = DEFAULT_HOST
        return ip_addr


    def run(self):
        autho = authorizer.authorizer()
        ftpserver.FTPHandler.authorizer = autho
        ftpserver.max_cons = 300
        ftpserver.max_cons_per_ip = 50
        ftpserver.FTPHandler.abstracted_fs = abstracted_fs.abstracted_fs
        if PASSIVE_PORTS:
            ftpserver.FTPHandler.passive_ports = PASSIVE_PORTS

        ftpserver.log = lambda msg: self.log(netsvc.LOG_INFO, msg)
        ftpserver.logline = lambda msg: None
        ftpserver.logerror = lambda msg: self.log(netsvc.LOG_ERROR, msg)

        address = (HOST or self.detect_ip_addr(), PORT)
        ftpd = ftpserver.FTPServer(address, ftpserver.FTPHandler)
        ftpd.serve_forever()
ds = ftp_server()
ds.daemon = True
ds.start()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
