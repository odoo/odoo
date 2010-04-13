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
from service import  http_server
from document_webdav import webdav_server
import tools
from caldav_fs import openerp_dav_handler
from tools.config import config

class DAVHandler(webdav_server.DAVHandler):    
    def setup(self):
        davpath = '/'+config.get_misc('webdav','vdir','webdav')
        self.baseuri = "http://%s:%d/"% (self.server.server_name,self.server.server_port)
        self.IFACE_CLASS  = openerp_dav_handler(self, self.verbose)    
    
  

handler = webdav_server.handler
if handler:    
    handler = DAVHandler    
    handler.debug = config.get_misc('webdav','debug',True)
    handler._config = webdav_server.conf

if http_server.httpd and handler:
    for vdir in http_server.httpd.server.vdirs:
        print vdir.handler ,  webdav_server.DAVHandler
        if vdir.handler == webdav_server.DAVHandler:                 
            vdir.handler  = handler
if http_server.httpsd and handler:
    for vdir in http_server.httpsd.server.vdirs:
        if vdir.handler == webdav_server.DAVHandler:
            vdir.handler = handler
