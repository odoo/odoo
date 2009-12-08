# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
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

from cache import memoize

CACHE_SIZE=20000

#hack for urlparse: add webdav in the net protocols
urlparse.uses_netloc.append('webdav')
urlparse.uses_netloc.append('webdavs')

class tinydav_handler(dav_interface):
	"""
	This class models a Tiny ERP interface for the DAV server
	"""
	PROPS={'DAV:': dav_interface.PROPS['DAV:'], }

	M_NS={ "DAV:" : dav_interface.M_NS['DAV:'], }

	def __init__(self,  parent, verbose=False):
		self.db_name = False
		self.directory_id=False
		self.db_name_list=[]
		self.parent = parent
		self.baseuri = parent.baseuri

        def get_propnames(self,uri):
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

#
#	def get_db(self,uri):
#		names=self.uri2local(uri).split('/')
#		self.db_name=False
#		if len(names) > 1:
#			self.db_name=self.uri2local(uri).split('/')[1]
#			if self.db_name=='':
#				raise Exception,'Plese specify Database name in folder'
#		return self.db_name
#

	def later_get_db_from_path(self,path):
		return "aaa"

	def urijoin(self,*ajoin):
		""" Return the base URI of this request, or even join it with the
		    ajoin path elements
		"""
		return self.baseuri+ '/'.join(ajoin)

	@memoize(4)
	def db_list(self):
		s = netsvc.LocalService('db')
		result = s.list()
		self.db_name_list=[]
		for db_name in result:
			db = pooler.get_db_only(db_name)
			cr = db.cursor()
			cr.execute("select id from ir_module_module where name = 'document' and state='installed' ")
			res=cr.fetchone()
			if res and len(res):
				self.db_name_list.append(db_name)
			cr.close()
		return self.db_name_list

	def get_childs(self,uri):
		""" return the child objects as self.baseuris for the given URI """
		self.parent.log_message('get childs: %s' % uri)
		if uri[-1]=='/':uri=uri[:-1]
		cr, uid, pool, dbname, uri2 = self.get_cr(uri)
		
		if not dbname:
			s = netsvc.LocalService('db')
			return map(lambda x: self.urijoin(x), self.db_list())
		result = []
		node = self.uri2object(cr,uid,pool, uri2[:])
		if not node:
			cr.close()
			raise DAV_NotFound(uri2)
		else:
		    fp = node.full_path()
		    if fp and len(fp):
			self.parent.log_message('childs: @%s' % fp)
			fp = '/'.join(fp)
		    else:
			fp = None
		    for d in node.children(cr):
			self.parent.log_message('child: %s' % d.path)
			if fp:
				result.append( self.urijoin(dbname,fp,d.path) )
			else:
				result.append( self.urijoin(dbname,d.path) )
		cr.close()
		return result

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

	def uri2object(self, cr,uid, pool,uri):
		if not uid:
			return None
		return pool.get('document.directory').get_object(cr, uid, uri)

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
			datas = node.get_data(cr)
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
		if node.type in ('collection','database'):
			return COLLECTION
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
			
		result = 'application/octet-stream'
		#if node.type=='collection':
			#result ='httpd/unix-directory'
		#else:
		result = node.mimetype
		return result
		#raise DAV_NotFound, 'Could not find %s' % path
	    finally:
	        cr.close()

	def mkcol(self,uri):
		""" create a new collection """
		self.parent.log_message('MKCOL: %s' % uri)
		if uri[-1]=='/':uri=uri[:-1]
		parent='/'.join(uri.split('/')[:-1])
		if not parent.startswith(self.baseuri):
			parent=self.baseuri + ''.join(parent[1:])
		if not uri.startswith(self.baseuri):
			uri=self.baseuri + ''.join(uri[1:])


		cr, uid, pool,dbname, uri2 = self.get_cr(uri)
		if not dbname:
			raise DAV_Error, 409
		node = self.uri2object(cr,uid,pool, uri2[:-1])
		object2=node and node.object2 or False
		object=node and node.object or False

		objname = uri2[-1]
		if not object:
			pool.get('document.directory').create(cr, uid, {
				'name': objname,
				'parent_id': False,
				'ressource_type_id': False,
				'ressource_id': False
			})
		else:
			pool.get('document.directory').create(cr, uid, {
				'name': objname,
				'parent_id': object.id,
				'ressource_type_id': object.ressource_type_id.id,
				'ressource_id': object2 and object2.id or False
			})

		cr.commit()
		cr.close()
		return True

	def put(self,uri,data,content_type=None):
		""" put the object into the filesystem """
		self.parent.log_message('Putting %s (%d), %s'%( unicode(uri,'utf8'), len(data), content_type))
		parent='/'.join(uri.split('/')[:-1])
		cr, uid, pool,dbname, uri2 = self.get_cr(uri)
		if not dbname:
			raise DAV_Forbidden
		try:
			node = self.uri2object(cr,uid,pool, uri2[:])
		except:
			node = False
		objname = uri2[-1]
		ext = objname.find('.') >0 and objname.split('.')[1] or False

		if not node:
			dir_node = self.uri2object(cr,uid,pool, uri2[:-1])
			if not dir_node:
				raise DAV_NotFound('Parent folder not found')
			try:
			    dir_node.create_child(cr,objname,data)
			except Exception,e:
			    import traceback
			    self.parent.log_error("Cannot create %s: %s", objname, str(e))
			    self.parent.log_message("Exc: %s",traceback.format_exc())
			    raise DAV_Forbidden
		else:
			try:
			    node.set_data(cr,data)
			except Exception,e:
			    import traceback
			    self.parent.log_error("Cannot save %s: %s", objname, str(e))
			    self.parent.log_message("Exc: %s",traceback.format_exc())
			    raise DAV_Forbidden
			
		cr.commit()

		return 201

	def rmcol(self,uri):
		""" delete a collection """
		if uri[-1]=='/':uri=uri[:-1]

		cr, uid, pool, dbname, uri2 = self.get_cr(uri)
		if True or not dbname: # *-*
			raise DAV_Error, 409
		node = self.uri2object(cr,uid,pool, uri2)
		object2=node and node.object2 or False
		object=node and node.object or False
		if object._table_name=='document.directory':
			if object.child_ids:
				raise DAV_Forbidden # forbidden
			if object.file_ids:
				raise DAV_Forbidden # forbidden
			res = pool.get('document.directory').unlink(cr, uid, [object.id])

		cr.commit()
		cr.close()
		return 204

	def rm(self,uri):
		if uri[-1]=='/':uri=uri[:-1]

		object=False
		cr, uid, pool,dbname, uri2 = self.get_cr(uri)
		#if not dbname:
		if True:
			raise DAV_Error, 409
		node = self.uri2object(cr,uid,pool, uri2)
		object2=node and node.object2 or False
		object=node and node.object or False
		if not object:
			raise DAV_NotFound

		self.parent.log_message(' rm %s "%s"'%(object._table_name,uri))
		if object._table_name=='ir.attachment':
			res = pool.get('ir.attachment').unlink(cr, uid, [object.id])
		else:
			raise DAV_Forbidden # forbidden
		parent='/'.join(uri.split('/')[:-1])
		cr.commit()
		cr.close()
		return 204

	### DELETE handlers (examples)
	### (we use the predefined methods in davcmd instead of doing
	### a rm directly
	###

	def delone(self,uri):
		""" delete a single resource

		You have to return a result dict of the form
		uri:error_code
		or None if everything's ok

		"""
		if uri[-1]=='/':uri=uri[:-1]
		res=delone(self,uri)
		parent='/'.join(uri.split('/')[:-1])
		return res

	def deltree(self,uri):
		""" delete a collection

		You have to return a result dict of the form
		uri:error_code
		or None if everything's ok
		"""
		if uri[-1]=='/':uri=uri[:-1]
		res=deltree(self,uri)
		parent='/'.join(uri.split('/')[:-1])
		return res


	###
	### MOVE handlers (examples)
	###

	def moveone(self,src,dst,overwrite):
		""" move one resource with Depth=0

		an alternative implementation would be

		result_code=201
		if overwrite:
			result_code=204
			r=os.system("rm -f '%s'" %dst)
			if r: return 412
		r=os.system("mv '%s' '%s'" %(src,dst))
		if r: return 412
		return result_code

		(untested!). This would not use the davcmd functions
		and thus can only detect errors directly on the root node.
		"""
		res=moveone(self,src,dst,overwrite)
		return res

	def movetree(self,src,dst,overwrite):
		""" move a collection with Depth=infinity

		an alternative implementation would be

		result_code=201
		if overwrite:
			result_code=204
			r=os.system("rm -rf '%s'" %dst)
			if r: return 412
		r=os.system("mv '%s' '%s'" %(src,dst))
		if r: return 412
		return result_code

		(untested!). This would not use the davcmd functions
		and thus can only detect errors directly on the root node"""

		res=movetree(self,src,dst,overwrite)
		return res

	###
	### COPY handlers
	###

	def copyone(self,src,dst,overwrite):
		""" copy one resource with Depth=0

		an alternative implementation would be

		result_code=201
		if overwrite:
			result_code=204
			r=os.system("rm -f '%s'" %dst)
			if r: return 412
		r=os.system("cp '%s' '%s'" %(src,dst))
		if r: return 412
		return result_code

		(untested!). This would not use the davcmd functions
		and thus can only detect errors directly on the root node.
		"""
		res=copyone(self,src,dst,overwrite)
		return res

	def copytree(self,src,dst,overwrite):
		""" copy a collection with Depth=infinity

		an alternative implementation would be

		result_code=201
		if overwrite:
			result_code=204
			r=os.system("rm -rf '%s'" %dst)
			if r: return 412
		r=os.system("cp -r '%s' '%s'" %(src,dst))
		if r: return 412
		return result_code

		(untested!). This would not use the davcmd functions
		and thus can only detect errors directly on the root node"""
		res=copytree(self,src,dst,overwrite)
		return res

	###
	### copy methods.
	### This methods actually copy something. low-level
	### They are called by the davcmd utility functions
	### copytree and copyone (not the above!)
	### Look in davcmd.py for further details.
	###

	def copy(self,src,dst):
		src=urllib.unquote(src)
		dst=urllib.unquote(dst)
		ct = self._get_dav_getcontenttype(src)
		data = self.get_data(src)
		self.put(dst,data,ct)
		return 201

	def copycol(self,src,dst):
		""" copy a collection.

		As this is not recursive (the davserver recurses itself)
		we will only create a new directory here. For some more
		advanced systems we might also have to copy properties from
		the source to the destination.
		"""
		print " copy a collection."
		return self.mkcol(dst)


	def exists(self,uri):
		""" test if a resource exists """
		result = False
		cr, uid, pool,dbname, uri2 = self.get_cr(uri)
		if not dbname:
			return True
		try:
			node = self.uri2object(cr,uid,pool, uri2)
			if node:
				result = True
		except:
			pass
		cr.close()
		return result

	@memoize(CACHE_SIZE)
	def is_collection(self,uri):
		""" test if the given uri is a collection """
		return self._get_dav_resourcetype(uri)==COLLECTION
