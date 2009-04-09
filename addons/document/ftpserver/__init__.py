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
PORT = config.get('ftp_server_port', 8021)
HOST = ''

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
        
        ftpserver.log = lambda msg: self.log(netsvc.LOG_INFO, msg)
        ftpserver.logline = lambda msg: None
        ftpserver.logerror = lambda msg: self.log(netsvc.LOG_ERROR, msg)

        address = (HOST, PORT)
        ftpd = ftpserver.FTPServer(address, ftpserver.FTPHandler)
        ftpd.serve_forever()
ds = ftp_server()
ds.start()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
