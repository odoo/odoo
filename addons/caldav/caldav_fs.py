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

from document_webdav import dav_fs
from document_webdav.cache import memoize
class openerp_dav_handler(dav_fs.openerp_dav_handler):    
    PROPS = {'DAV:': dav_fs.openerp_dav_handler.PROPS['DAV:'] + 
                     ('owner',),
            'http://calendarserver.org/ns/': ('getctag')}

    M_NS = { "DAV:" : dav_fs.openerp_dav_handler.M_NS['DAV:'],
           "http://calendarserver.org/ns/" : '_get_dav'}    

    @memoize(dav_fs.CACHE_SIZE)
    def _get_dav_getctag(self,uri):
        print """ return the CTag of an object """
        self.parent.log_message('get ctag: %s' % uri)
        if uri[-1]=='/':uri=uri[:-1]
        result = 0
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        if not dbname:
            cr.close()
            return '0'
        node = self.uri2object(cr, uid, pool, uri2)
        if not node:
            cr.close()
            raise DAV_NotFound(uri2)
        result = node.get_ctag(cr)
        cr.close()
        return str(result)

    @memoize(dav_fs.CACHE_SIZE)
    def _get_dav_owner(self,uri):
        print """ return the Owner of an object """
        self.parent.log_message('get ctag: %s' % uri)
        if uri[-1]=='/':uri=uri[:-1]
        result = 0
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        if not dbname:
            cr.close()
            return '0'
        node = self.uri2object(cr, uid, pool, uri2)
        if not node:
            cr.close()
            raise DAV_NotFound(uri2)
        result = node.get_owner(cr)
        cr.close()
        return str(result)



