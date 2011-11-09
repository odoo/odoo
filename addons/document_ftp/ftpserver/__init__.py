# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import threading
import ftpserver
import authorizer
import abstracted_fs
import netsvc
from tools import config

def start_server():
    HOST = config.get('ftp_server_host', '127.0.0.1')
    PORT = int(config.get('ftp_server_port', '8021'))
    PASSIVE_PORTS = None
    pps = config.get('ftp_server_passive_ports', '').split(':')
    if len(pps) == 2:
        PASSIVE_PORTS = int(pps[0]), int(pps[1])

    class ftp_server(threading.Thread):
        def log(self, level, message):
            logger = netsvc.Logger()
            logger.notifyChannel('FTP', level, message)

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

            ftpd = ftpserver.FTPServer((HOST, PORT), ftpserver.FTPHandler)
            ftpd.serve_forever()

    if HOST.lower() == 'none':
        netsvc.Logger().notifyChannel("FTP", netsvc.LOG_INFO, "\n Server FTP Not Started\n")
    else:
        netsvc.Logger().notifyChannel("FTP", netsvc.LOG_INFO, "\n Serving FTP on %s:%s\n" % (HOST, PORT))
        ds = ftp_server()
        ds.daemon = True
        ds.start()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

