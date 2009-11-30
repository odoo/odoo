# -*- encoding: utf-8 -*-

#
# Copyright P. Christeas <p_christ@hol.gr> 2008,2009
#
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
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
###############################################################################


import netsvc
from dav_fs import tinydav_handler
from tools.config import config
from DAV.WebDAVServer import DAVRequestHandler
from service.websrv_lib import HTTPDir,FixSendError

class DAVHandler(FixSendError,DAVRequestHandler):
    verbose = False
	
    def get_userinfo(self,user,pw):
	print "get_userinfo"
	return False
    def _log(self, message):
	netsvc.Logger().notifyChannel("webdav",netsvc.LOG_DEBUG,message)
	
    def handle(self):
        pass

    def finish(self):
        pass

    def setup(self):
	davpath = '/'+config.get_misc('webdav','vdir','webdav')+'/'
	self.baseuri = "http://%s:%d%s"% (self.server.server_name,self.server.server_port,davpath)
	self.IFACE_CLASS  = tinydav_handler(self)
	pass
	
    def log_message(self, format, *args):
	netsvc.Logger().notifyChannel('webdav',netsvc.LOG_DEBUG_RPC,format % args)

    def log_error(self, format, *args):
	netsvc.Logger().notifyChannel('xmlrpc',netsvc.LOG_WARNING,format % args)


try:
	from service.http_server import reg_http_service,OpenERPAuthProvider
	if (config.get_misc('webdav','enable',False)):
		davpath = '/'+config.get_misc('webdav','vdir','webdav')+'/'
		handler = DAVHandler
		handler.verbose = config.get_misc('webdav','verbose',True)
		handler.debug = config.get_misc('webdav','debug',True)
		reg_http_service(HTTPDir(davpath,DAVHandler,OpenERPAuthProvider()))
		netsvc.Logger().notifyChannel('webdav',netsvc.LOG_INFO,"WebDAV service registered at path: %s/ "% davpath)
except Exception, e:
	logger = netsvc.Logger()
	logger.notifyChannel('webdav', netsvc.LOG_ERROR, 'Cannot launch webdav: %s' % e)

#eof



