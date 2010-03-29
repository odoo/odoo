# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import pooler

import base64
import sys
import os
import time
from string import joinfields, split, lower

from service import security

import netsvc
import urlparse

from DAV.constants import COLLECTION, OBJECT
from DAV.errors import *
from DAV.iface import *
import urllib

from DAV.davcmd import copyone, copytree, moveone, movetree, delone, deltree
from caldav_cache import memoize
from tools import misc
CACHE_SIZE=20000


class tinydav_handler(dav_interface):
    """
    This class models a Tiny ERP interface for the DAV server
    """
    PROPS={'DAV:': dav_interface.PROPS['DAV:'], }

    M_NS={ "DAV:" : dav_interface.M_NS['DAV:'], }

    def __init__(self,  parent, verbose=False):
        self.db_name = False        
        self.parent = parent
        self.baseuri = parent.baseuri

    def get_propnames(self, uri):
        props = self.PROPS
        self.parent.log_message('get propnames: %s' % uri)
        if uri[-1]=='/':uri=uri[:-1]
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        if not dbname:
            cr.close()
            return props
        node = self.uri2object(cr,uid,pool, uri2)
        if node:
            props.update(node.get_dav_props(cr))
        cr.close()
        return props

    def get_prop(self,uri,ns,propname):
        """ return the value of a given property

            uri        -- uri of the object to get the property of
            ns        -- namespace of the property
            pname        -- name of the property
         """
        if self.M_NS.has_key(ns):
           return dav_interface.get_prop(self,uri,ns,propname)

        if uri[-1]=='/':uri=uri[:-1]
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        if not dbname:
            cr.close()
            raise DAV_NotFound
        node = self.uri2object(cr,uid,pool, uri2)
        if not node:
            cr.close()
            raise DAV_NotFound
        res = node.get_dav_eprop(cr,ns,propname)
        cr.close()
        return res

    def urijoin(self,*ajoin):
        """ Return the base URI of this request, or even join it with the
            ajoin path elements
        """
        return self.baseuri+ '/'.join(ajoin)        

    def uri2local(self, uri):
        uparts=urlparse.urlparse(uri)
        reluri=uparts[2]
        if reluri and reluri[-1]=="/":
            reluri=reluri[:-1]
        return reluri

    #
    # pos: -1 to get the parent of the uri
    #
    def get_cr(self, uri):        
        pdb = self.parent.auth_proxy.last_auth
        reluri = self.uri2local(uri)        
        try:
            dbname = reluri.split('/')[2]
        except:
            dbname = False
        if not dbname:
            return None, None, None, False, None
        if not pdb and dbname:
            # if dbname was in our uri, we should have authenticated
            # against that.
            raise Exception("Programming error")        
        assert pdb == dbname, " %s != %s" %(pdb, dbname)
        user, passwd, dbn2, uid = self.parent.auth_proxy.auth_creds[pdb]
        db,pool = pooler.get_db_and_pool(dbname)
        cr = db.cursor()
        uri2 = reluri.split('/')[3:]
        return cr, uid, pool, dbname, uri2

    def uri2object(self, cr, uid, pool, uri):
        if not uid:
            return None
        return pool.get('basic.calendar').get_calendar_object(cr, uid, uri)

    def get_data(self,uri):
        self.parent.log_message('GET: %s' % uri)
        if uri[-1]=='/':uri=uri[:-1]
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        try:
            if not dbname:
                raise DAV_Error, 409
            node = self.uri2object(cr,uid,pool, uri2)
            if not node:
                raise DAV_NotFound(uri2)
            try:                
                datas = node.get_data(cr, uid)
            except TypeError,e:
                import traceback
                self.parent.log_error("GET typeError: %s", str(e))
                self.parent.log_message("Exc: %s",traceback.format_exc())
                raise DAV_Forbidden
            except IndexError,e :
                self.parent.log_error("GET IndexError: %s", str(e))
                raise DAV_NotFound(uri2)
            except Exception,e:
                import traceback
                self.parent.log_error("GET exception: %s",str(e))
                self.parent.log_message("Exc: %s", traceback.format_exc())
                raise DAV_Error, 409
            return datas
        finally:
            cr.close()

    @memoize(CACHE_SIZE)
    def _get_dav_resourcetype(self,uri):
        """ return type of object """
        self.parent.log_message('get RT: %s' % uri)
        if uri[-1]=='/':uri=uri[:-1]
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        try:
            if not dbname:
                return COLLECTION
            node = self.uri2object(cr,uid,pool, uri2)
            if not node:
                raise DAV_NotFound(uri2)            
            return OBJECT
        finally:
            cr.close()

    def _get_dav_displayname(self,uri):
        self.parent.log_message('get DN: %s' % uri)
        if uri[-1]=='/':uri=uri[:-1]
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        if not dbname:
            cr.close()
            return COLLECTION
        node = self.uri2object(cr,uid,pool, uri2)
        if not node:
            cr.close()
            raise DAV_NotFound(uri2)
        cr.close()
        return node.displayname

    @memoize(CACHE_SIZE)
    def _get_dav_getcontentlength(self,uri):
        """ return the content length of an object """
        self.parent.log_message('get length: %s' % uri)
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
        result = node.content_length or 0
        cr.close()
        return str(result)

    @memoize(CACHE_SIZE)
    def _get_dav_getetag(self,uri):
        """ return the ETag of an object """
        self.parent.log_message('get etag: %s' % uri)
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
        result = node.get_etag(cr)
        cr.close()
        return str(result)

    @memoize(CACHE_SIZE)
    def get_lastmodified(self,uri):
        """ return the last modified date of the object """
        if uri[-1]=='/':uri=uri[:-1]
        today = time.time()
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        try:
            if not dbname:
                return today
            node = self.uri2object(cr,uid,pool, uri2)
            if not node:
                raise DAV_NotFound(uri2)
            if node.write_date:
                return time.mktime(time.strptime(node.write_date,'%Y-%m-%d %H:%M:%S'))
            else:
                return today
        finally:
            cr.close()

    @memoize(CACHE_SIZE)
    def get_creationdate(self,uri):
        """ return the last modified date of the object """

        if uri[-1]=='/':uri=uri[:-1]
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        try:
            if not dbname:
                raise DAV_Error, 409
            node = self.uri2object(cr,uid,pool, uri2)
            if not node:
                raise DAV_NotFound(uri2)
            if node.create_date:
                result = time.strptime(node.create_date,'%Y-%m-%d %H:%M:%S')
            else:
                result = time.gmtime()
            return result
        finally:
            cr.close()

    @memoize(CACHE_SIZE)
    def _get_dav_getcontenttype(self,uri):
        self.parent.log_message('get contenttype: %s' % uri)
        if uri[-1]=='/':uri=uri[:-1]
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        try:
            if not dbname:
                return 'httpd/unix-directory'
            node = self.uri2object(cr,uid,pool, uri2)
            if not node:
                raise DAV_NotFound(uri2)
            result = node.mimetype
            return result
            #raise DAV_NotFound, 'Could not find %s' % path
        finally:
            cr.close()

    

    def put(self, uri, data, content_type=None):
        """ put the object into the filesystem """
        self.parent.log_message('Putting %s (%d), %s'%( misc.ustr(uri), len(data), content_type))
        parent='/'.join(uri.split('/')[:-1])
        cr, uid, pool,dbname, uri2 = self.get_cr(uri)        
        if not dbname:
            raise DAV_Forbidden
        try:
            node = self.uri2object(cr,uid,pool, uri2[:])
        except:
            node = False        

        if not node:
            raise DAV_Forbidden
        else:
            try:
                node.set_data(cr, uid, data)                
            except Exception,e:
                import traceback                
                self.parent.log_error("Cannot save :%s", str(e))
                self.parent.log_message("Exc: %s",traceback.format_exc())
                raise DAV_Forbidden
            
        cr.commit()
        cr.close()
        return 201

    


    def exists(self,uri):
        """ test if a resource exists """
        result = False
        cr, uid, pool,dbname, uri2 = self.get_cr(uri)
        if not dbname:
            cr.close()
            return True
        try:
            node = self.uri2object(cr,uid,pool, uri2)
            if node:
                result = True
        except:
            pass
        cr.close()
        return result   
