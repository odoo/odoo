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

from document_webdav import webdav
import tools
from DAV.propfind import PROPFIND
import urlparse
urlparse.uses_netloc.append('caldav')
urlparse.uses_netloc.append('caldavs')
super_mk_prop_response = webdav.mk_prop_response
def mk_prop_response(self,uri,good_props,bad_props,doc):                
    res = super_mk_prop_response(self, uri,good_props,bad_props,doc)    
    uris = uri.split('/') 
    calendar = False    
    if 'http://calendarserver.org/ns/' in good_props or 'http://calendarserver.org/ns/' in bad_props:
        calendar = True
    if calendar:
        ad = doc.createElement('calendar')
        ad.setAttribute('xmlns', 'urn:ietf:params:xml:ns:caldav')        
        cols = res.getElementsByTagName('D:collection')
        if cols:
            cols[0].parentNode.appendChild(ad)
                #cols[0].parentNode.appendChild(vc)
    return res

PROPFIND.mk_prop_response = mk_prop_response
