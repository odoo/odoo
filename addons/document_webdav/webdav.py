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

import xml.dom.minidom
domimpl = xml.dom.minidom.getDOMImplementation()
import urlparse
import urllib
from DAV import utils
from DAV.propfind import PROPFIND
import tools


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

