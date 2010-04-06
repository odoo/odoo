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
import tools
from dav_fs import tinydav_handler
from tools.config import config
from DAV.WebDAVServer import DAVRequestHandler
from service.websrv_lib import HTTPDir,FixSendError
from DAV.propfind import PROPFIND

import xml.dom.minidom
domimpl = xml.dom.minidom.getDOMImplementation()
import urlparse
import urllib
from DAV import utils

super_mk_prop_response = PROPFIND.mk_prop_response
def mk_prop_response(self,uri,good_props,bad_props,doc):        
    """ make a new <prop> result element 

    We differ between the good props and the bad ones for
    each generating an extra <propstat>-Node (for each error
    one, that means).
    
    """      
    re=doc.createElement("D:response")
    # append namespaces to response
    nsnum=0
    for nsname in self.namespaces:
        re.setAttribute("xmlns:ns"+str(nsnum),nsname)
        nsnum=nsnum+1
    
    # write href information
    uparts=urlparse.urlparse(uri)
    fileloc=uparts[2]
    href=doc.createElement("D:href")
    huri=doc.createTextNode(uparts[0]+'://'+'/'.join(uparts[1:2]) + urllib.quote(fileloc))
    href.appendChild(huri)
    re.appendChild(href)

    # write good properties
    ps=doc.createElement("D:propstat")
    if good_props:
        re.appendChild(ps)

    gp=doc.createElement("D:prop")
    for ns in good_props.keys():
        ns_prefix="ns"+str(self.namespaces.index(ns))+":"
        for p,v in good_props[ns].items():            
            if not v:
                pass
            pe=doc.createElement(ns_prefix+str(p))
            if hasattr(v, '__class__') and v.__class__.__name__ == 'Element':
                pe.appendChild(v)
            else:
                if p=="resourcetype":
                    if v==1:
                        ve=doc.createElement("D:collection")
                        pe.appendChild(ve)
                else:
                    ve=doc.createTextNode(tools.ustr(v))
                    pe.appendChild(ve)

            gp.appendChild(pe)
    
    ps.appendChild(gp)
    s=doc.createElement("D:status")
    t=doc.createTextNode("HTTP/1.1 200 OK")
    s.appendChild(t)
    ps.appendChild(s)
    re.appendChild(ps)

    # now write the errors!
    if len(bad_props.items()):

        # write a propstat for each error code
        for ecode in bad_props.keys():
            ps=doc.createElement("D:propstat")
            re.appendChild(ps)
            bp=doc.createElement("D:prop")
            ps.appendChild(bp)

            for ns in bad_props[ecode].keys():
                ns_prefix="ns"+str(self.namespaces.index(ns))+":"
            
            for p in bad_props[ecode][ns]:
                pe=doc.createElement(ns_prefix+str(p))
                bp.appendChild(pe)
            
            s=doc.createElement("D:status")
            t=doc.createTextNode(utils.gen_estring(ecode))
            s.appendChild(t)
            ps.appendChild(s)
            re.appendChild(ps)

    # return the new response element
    return re
    

PROPFIND.mk_prop_response = mk_prop_response

def OpenDAVConfig(**kw):
    class OpenDAV:
        def __init__(self, **kw):
            self.__dict__.update(**kw)

    class Config:
        DAV = OpenDAV(**kw)

    return Config()

class DAVHandler(FixSendError,DAVRequestHandler):
    verbose = False
    
    def get_userinfo(self,user,pw):
        print "get_userinfo"
        return False
    def _log(self, message):
        netsvc.Logger().notifyChannel("webdav",netsvc.LOG_DEBUG,message)
    
    def handle(self):
        self._init_buffer()

    def finish(self):
        pass

    def get_db_from_path(self, uri):
        if uri or uri == '/':
            dbs = self.IFACE_CLASS.db_list()
            res = len(dbs) and dbs[0] or False
        else:
            res =  self.IFACE_CLASS.get_db(uri)        
        return res

    def setup(self):
        davpath = '/'+config.get_misc('webdav','vdir','webdav')
        self.baseuri = "http://%s:%d/"% (self.server.server_name,self.server.server_port)
        self.IFACE_CLASS  = tinydav_handler(self, self.verbose)
        
    
    def log_message(self, format, *args):
        netsvc.Logger().notifyChannel('webdav',netsvc.LOG_DEBUG_RPC,format % args)

    def log_error(self, format, *args):
        netsvc.Logger().notifyChannel('xmlrpc',netsvc.LOG_WARNING,format % args)


try:
    from service.http_server import reg_http_service,OpenERPAuthProvider   

    if (config.get_misc('webdav','enable',True)):
        directory = '/'+config.get_misc('webdav','vdir','webdav') 
        handler = DAVHandler
        verbose = config.get_misc('webdav','verbose',True)
        handler.debug = config.get_misc('webdav','debug',True)
        _dc = { 'verbose' : verbose,
                'directory' : directory,
                'lockemulation' : False,
                    
                }

        conf = OpenDAVConfig(**_dc)
        handler._config = conf
        reg_http_service(HTTPDir(directory,DAVHandler,OpenERPAuthProvider()))
        netsvc.Logger().notifyChannel('webdav',netsvc.LOG_INFO,"WebDAV service registered at path: %s/ "% directory)
except Exception, e:
    logger = netsvc.Logger()
    logger.notifyChannel('webdav', netsvc.LOG_ERROR, 'Cannot launch webdav: %s' % e)

#eof



