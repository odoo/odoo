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

import base64
import StringIO
from osv import osv, fields
from osv.orm import except_orm
import urlparse
import pooler
from tools.safe_eval import safe_eval

import os
import time

#
# An object that represent an uri
#   path: the uri of the object
#   content: the Content it belongs to (_print.pdf)
#   type: content or collection
#       content: objct = res.partner
#       collection: object = directory, object2 = res.partner
#       file: objct = ir.attachement
#   root: if we are at the first directory of a ressource
#

def get_node_context(cr, uid, context):
    return node_context(cr,uid,context)

class node_context(object):
    """ This is the root node, representing access to some particular
        context """
    cached_roots = {}

    def __init__(self, cr, uid, context=None):        
        self.dbname = cr.dbname
        self.uid = uid
        self.context = context
        self._dirobj = pooler.get_pool(cr.dbname).get('document.directory')
        assert self._dirobj
        self.rootdir = False #self._dirobj._get_root_directory(cr,uid,context)

    def get_uri(self, cr,  uri):
        """ Although this fn passes back to doc.dir, it is needed since
        it is a potential caching point """            
        (ndir, duri) =  self._dirobj._locate_child(cr,self.uid, self.rootdir,uri, None, self)          
        while duri:                    
            ndir = ndir.child(cr, duri[0])            
            if not ndir:
                return False            
            duri = duri[1:] 
        return ndir




class node_class(object):
    """ this is a superclass for our inodes
        It is an API for all code that wants to access the document files. 
        Nodes have attributes which contain usual file properties
        """
    our_type = 'baseclass'
    def __init__(self, path, parent, context):
        assert isinstance(context,node_context)
        assert (not parent ) or isinstance(parent,node_class)
        self.path = path
        self.context = context
        self.type=self.our_type
        self.parent = parent
        self.mimetype = 'application/octet-stream'
        self.create_date = None
        self.write_date = None
        self.content_length = 0
        # dynamic context:
        self.dctx = {}
        if parent:
            self.dctx = parent.dctx.copy()
        self.displayname = 'Object'
    
    def full_path(self):
        """ Return the components of the full path for some
            node. 
            The returned list only contains the names of nodes.
        """
        if self.parent:
            s = self.parent.full_path()
        else:
            s = []
        if isinstance(self.path,list):
            s+=self.path
        else:
            s.append(self.path)
        return s #map(lambda x: '/' +x, s)

    def children(self, cr, domain=None):
        print "node_class.children()"
        return [] #stub

    def child(self,cr, name, domain=None):
        print "node_class.child()"
        return None

    def path_get(self):
        print "node_class.path_get()"
        return False
    
    def get_data(self,cr):
        raise TypeError('no data for %s'% self.type)

    def _get_storage(self,cr):
        raise RuntimeError("no storage for base class")

    def get_etag(self,cr):
        """ Get a tag, unique per object + modification.
    
            see. http://tools.ietf.org/html/rfc2616#section-13.3.3 """
        return self._get_ttag(cr) + ':' + self._get_wtag(cr)

    def _get_wtag(self,cr):
        """ Return the modification time as a unique, compact string """
        if self.write_date:
            wtime = time.mktime(time.strptime(self.write_date,'%Y-%m-%d %H:%M:%S'))
        else: wtime = time.time()
        return str(wtime)
    
    def _get_ttag(self,cr):
        """ Get a unique tag for this type/id of object.
            Must be overriden, so that each node is uniquely identified.
        """
        print "node_class.get_ttag()",self
        raise RuntimeError("get_etag stub()")
    
    def get_dav_props(self, cr):
        """ If this class has special behaviour for GroupDAV etc, export
        its capabilities """
        return {}

    def get_dav_eprop(self,cr,ns,prop):
        return None

    def get_domain(self, cr, filters):
        return []

class node_database(node_class):
    """ A node representing the database directory
        
    """
    our_type = 'database'
    def __init__(self, path=[], parent=False, context=None):
        super(node_database,self).__init__(path, parent, context)

    def children(self, cr, domain=None):
        res = self._child_get(cr, domain=domain) + self._file_get(cr)        
        return res

    def child(self, cr, name, domain=None):        
        res = self._child_get(cr, name, domain=None)
        if res:
            return res[0]
        res = self._file_get(cr,name)
        if res:
            return res[0]
        return None

    def _child_get(self, cr, name=False, parent_id=False, domain=None):
        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        where = [('parent_id','=',parent_id)]                              
        if name:
            where.append(('name','=',name))
        if not domain:
            domain = []

        where2 = where + domain + [('type', '=', 'directory')]
        ids = dirobj.search(cr, uid, where2, context=ctx)
        res = []        
        for dirr in dirobj.browse(cr,uid,ids,context=ctx):            
            res.append(node_dir(dirr.name,self,self.context,dirr))
        
        where2 = where + domain + [('type', '=', 'ressource'), ('ressource_parent_type_id','=',False)]
        ids = dirobj.search(cr, uid, where2, context=ctx)        
        for dirr in dirobj.browse(cr,uid,ids,context=ctx):                       
            res.append(node_res_dir(dirr.name,self,self.context,dirr))
        
        fil_obj = dirobj.pool.get('ir.attachment')        
        ids = fil_obj.search(cr,uid,where,context=ctx)
        if ids:
            for fil in fil_obj.browse(cr,uid,ids,context=ctx):
                res.append(node_file(fil.name,self,self.context,fil))
        return res

    def _file_get(self,cr, nodename=False, directory_id=False):
        res = []
        cntobj = self.context._dirobj.pool.get('document.directory.content')
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        where = [('directory_id','=',directory_id) ]
        ids = cntobj.search(cr, uid, where, context=ctx)
        for content in cntobj.browse(cr, uid, ids, context=ctx):
            res3 = cntobj._file_get(cr, self, nodename, content)
            if res3:
                res.extend(res3)

        return res

    def _get_ttag(self,cr):
        return 'db-%s' % cr.dbname
        

class node_dir(node_database):
    our_type = 'collection'
    def __init__(self,path, parent, context, dirr, dctx=None):
        super(node_dir,self).__init__(path, parent,context)
        self.dir_id = dirr and dirr.id or False
        #todo: more info from dirr
        self.mimetype = 'application/x-directory'
            # 'httpd/unix-directory'
        self.create_date = dirr and dirr.create_date or False
        self.domain = dirr and dirr.domain or []
        self.res_model = dirr and dirr.ressource_type_id and dirr.ressource_type_id.model or False
        # TODO: the write date should be MAX(file.write)..
        self.write_date = dirr and (dirr.write_date or dirr.create_date) or False
        self.content_length = 0
        if dctx:
            self.dctx.update(dctx)
        dc2 = self.context.context
        dc2.update(self.dctx)
        dc2['dir_id'] = self.dir_id
        self.displayname = dirr and dirr.name or False
        if dirr and dirr.dctx_ids:
            for dfld in dirr.dctx_ids:
                try:
                    self.dctx['dctx_' + dfld.field] = safe_eval(dfld.expr,dc2)
                except Exception,e:
                    print "Cannot eval %s" % dfld.expr
                    print e
                    pass

    
    #def get_data(self,cr):
    #    return ''

    

    def _file_get(self,cr, nodename=False):
        return super(node_dir,self)._file_get(cr, nodename, self.dir_id)       

    

    def _child_get(self, cr, name=None, domain=None):
        return super(node_dir,self)._child_get(cr, name, self.dir_id, domain=domain)

    def create_child_collection(self, cr, objname):
        object2 = False            
        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        obj = dirobj.browse(cr, uid, self.dir_id)            
        if obj and (obj.type == 'ressource') and not object2:
            raise OSError(1, 'Operation not permited.')

        #objname = uri2[-1]
        val = {
                'name': objname,
                'ressource_parent_type_id': obj and obj.ressource_type_id.id or False,
                'ressource_id': object2 and object2.id or False,
                'parent_id' : obj and obj.id or False
        }                 
        
        return dirobj.create(cr, uid, val)
        
    
    def create_child(self,cr,path,data):
        """ API function to create a child file object and node
            Return the node_* created
        """
        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        fil_obj=dirobj.pool.get('ir.attachment')
        val = {
            'name': path,
            'datas_fname': path,
            'parent_id': self.dir_id,
            # Datas are not set here
        }

        fil_id = fil_obj.create(cr,uid, val, context=ctx)
        fil = fil_obj.browse(cr,uid,fil_id,context=ctx)
        fnode = node_file(path,self,self.context,fil)
        fnode.set_data(cr,data,fil)
        return fnode

    def get_etag(self, cr):
        """ Get a tag, unique per object + modification.

            see. http://tools.ietf.org/html/rfc2616#section-13.3.3 """
        return self._get_ttag(cr) + ':' + self._get_wtag(cr)

    def _get_wtag(self, cr):
        """ Return the modification time as a unique, compact string """
        if self.write_date:
            wtime = time.mktime(time.strptime(self.write_date, '%Y-%m-%d %H:%M:%S'))
        else: wtime = time.time()
        return str(wtime)    
    
    def _get_ttag(self,cr):
        return 'dir-%d' % self.dir_id

class node_res_dir(node_class):
    """ A special sibling to node_dir, which does only contain dynamically
        created folders foreach resource in the foreign model.
        All folders should be of type node_res_obj and merely behave like
        node_dirs (with limited domain).
    """
    our_type = 'collection'
    def __init__(self,path, parent, context, dirr, dctx=None ):
        super(node_res_dir,self).__init__(path, parent,context)
        self.dir_id = dirr.id
        #todo: more info from dirr
        self.mimetype = 'application/x-directory'
                        # 'httpd/unix-directory'
        self.create_date = dirr.create_date
        # TODO: the write date should be MAX(file.write)..
        self.write_date = dirr.write_date or dirr.create_date
        self.content_length = 0
        self.res_model = dirr.ressource_type_id and dirr.ressource_type_id.model or False
        self.resm_id = dirr.ressource_id
        self.namefield = dirr.resource_field or 'name'
        self.displayname = dirr.name
        # Important: the domain is evaluated using the *parent* dctx!        
        self.domain = dirr.domain
        self.ressource_tree = dirr.ressource_tree
        # and then, we add our own vars in the dctx:
        if dctx:
            self.dctx.update(dctx)
    
        # and then, we prepare a dctx dict, for deferred evaluation:
        self.dctx_dict = {}
        for dfld in dirr.dctx_ids:
            self.dctx_dict['dctx_' + dfld.field] = dfld.expr

    def children(self, cr, domain=None):
        return self._child_get(cr, domain=domain)

    def child(self,cr, name, domain=None):        
        res = self._child_get(cr, name, domain=domain)
        if res:
            return res[0]
        return None

    def _child_get(self,cr, name = None, domain=None):
        """ return virtual children of resource, based on the
            foreign object.
        
            Note that many objects use NULL for a name, so we should
            better call the name_search(),name_get() set of methods
        """
        obj = self.context._dirobj.pool.get(self.res_model)
        if not obj:
            print "couldn't find model", self.res_model
            return []
        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        where = []
        if self.domain:
            where += safe_eval(self.domain, self.dctx)
        if self.resm_id:
            where.append(('id','=',self.resm_id))
    
        if name:
            where.append((self.namefield,'=',name))
        
        # print "Where clause for %s" % self.res_model, where
        if self.ressource_tree:
            object2 = False
            if self.resm_id:
                object2 = dirobj.pool.get(self.res_model).browse(cr, uid, self.resm_id) or False                
            if obj._parent_name in obj.fields_get(cr, uid):                    
                where.append((obj._parent_name,'=',object2 and object2.id or False))
                
        resids = obj.search(cr,uid, where, context=ctx)
        res = []        
        for bo in obj.browse(cr,uid,resids,context=ctx):
            if not bo:
                continue
            name = getattr(bo,self.namefield)
            if not name:
                continue
                # Yes! we can't do better but skip nameless records.     
             
            res.append(node_res_obj(name, self.dir_id, self, self.context, self.res_model, bo))
        return res

    def _get_ttag(self,cr):
        return 'rdir-%d' % self.dir_id

class node_res_obj(node_class):
    """ A special sibling to node_dir, which does only contain dynamically
        created folders foreach resource in the foreign model.
        All folders should be of type node_res_obj and merely behave like
        node_dirs (with limited domain).
        """
    our_type = 'collection'
    def __init__(self, path, dir_id, parent, context, res_model, res_bo, res_id = None):
        super(node_res_obj,self).__init__(path, parent,context)
        assert parent
        #todo: more info from dirr            
        self.dir_id = dir_id
        self.mimetype = 'application/x-directory'
                        # 'httpd/unix-directory'
        self.create_date = parent.create_date
        # TODO: the write date should be MAX(file.write)..
        self.write_date = parent.write_date
        self.content_length = 0
        self.res_model = res_model
        self.domain = parent.domain
        self.displayname = path  
        self.dctx_dict = parent.dctx_dict      
        if res_bo:            
            self.res_id = res_bo.id            
            dc2 = self.context.context
            dc2.update(self.dctx)
            dc2['res_model'] = res_model
            dc2['res_id'] = res_bo.id
            dc2['this'] = res_bo            
            for fld,expr in self.dctx_dict.items():
                try:
                    self.dctx[fld] = safe_eval(expr,dc2)
                except Exception,e:
                    print "Cannot eval %s for %s" % (expr, fld)
                    print e
                    pass
        else:
            self.res_id = res_id

    def children(self, cr, domain=None):        
        return self._child_get(cr, domain=domain) + self._file_get(cr)

    def child(self,cr, name, domain=None):            
        res = self._child_get(cr, name, domain=domain)                
        if res:
            return res[0]
        res = self._file_get(cr,name)
        if res:
            return res[0]
        return None

    def _file_get(self,cr, nodename=False):
        res = []
        cntobj = self.context._dirobj.pool.get('document.directory.content')
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        where = [('directory_id','=',self.dir_id) ]
        #if self.domain:
        #    where.extend(self.domain)
        # print "res_obj file_get clause", where
        ids = cntobj.search(cr,uid,where,context=ctx)
        for content in cntobj.browse(cr,uid,ids,context=ctx):
            res3 = cntobj._file_get(cr,self,nodename,content, context=ctx)
            if res3:
                res.extend(res3)

        return res

    def get_dav_props(self, cr):
        res = {}
        cntobj = self.context._dirobj.pool.get('document.directory.content')
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        where = [('directory_id','=',self.dir_id) ]
        ids = cntobj.search(cr,uid,where,context=ctx)
        for content in cntobj.browse(cr,uid,ids,context=ctx):
            if content.extension == '.ics': # FIXME: call the content class!
                res['http://groupdav.org/'] = ('resourcetype',)
        return res

    def get_dav_eprop(self,cr,ns,prop):
        if ns != 'http://groupdav.org/' or prop != 'resourcetype':
            print "Who asked for %s:%s?" % (ns,prop)
            return None
        res = {}
        cntobj = self.context._dirobj.pool.get('document.directory.content')
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        where = [('directory_id','=',self.dir_id) ]
        ids = cntobj.search(cr,uid,where,context=ctx)
        for content in cntobj.browse(cr,uid,ids,context=ctx):
            if content.extension == '.ics': # FIXME: call the content class!
                return ('vevent-collection','http://groupdav.org/')
        return None

    def _child_get(self,cr, name=None, domain=None):        
        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        directory = dirobj.browse(cr, uid, self.dir_id)
        obj = dirobj.pool.get(self.res_model)
        where = []
        res = []        
        if name:
            where.append(('name','=',name))   
       
        # Directory Structure display in tree structure
        if self.res_id and directory.ressource_tree:  
            where1 = []                 
            if obj._parent_name in obj.fields_get(cr, uid):                    
                where1 = where + [(obj._parent_name, '=', self.res_id)]
            resids = obj.search(cr,uid, where1, context=ctx)                        
            for bo in obj.browse(cr,uid,resids,context=ctx):
                namefield = directory.resource_field or 'name'
                if not bo:
                    continue
                res_name = getattr(bo, namefield)
                if not res_name:
                    continue                
                res.append(node_res_obj(res_name, self.dir_id, self, self.context, self.res_model, res_bo = bo))        
        
        
        where2 = where + [('parent_id','=',self.dir_id) ]        
        ids = dirobj.search(cr, uid, where2, context=ctx) 
        for dirr in dirobj.browse(cr, uid, ids, context=ctx):
            if dirr.type == 'directory':
                res.append(node_res_obj(dirr.name, dirr.id, self, self.context, self.res_model, res_bo = None, res_id = self.res_id))
            elif dirr.type == 'ressource':
                # child resources can be controlled by properly set dctx
                res.append(node_res_dir(dirr.name,self,self.context, dirr, {'active_id': self.res_id}))
        

       
        
        fil_obj = dirobj.pool.get('ir.attachment')
        where3 = where2  + [('res_model', '=', self.res_model), ('res_id','=',self.res_id)]
        # print "where clause for dir_obj", where2
        ids = fil_obj.search(cr, uid, where3, context=ctx)
        if ids:
            for fil in fil_obj.browse(cr, uid, ids, context=ctx):
                res.append(node_file(fil.name, self, self.context, fil))
    
        
        # Get Child Ressource Directories                
        if directory.ressource_type_id and directory.ressource_type_id.id:              
            where4 = where + [('ressource_parent_type_id','=',directory.ressource_type_id.id)]            
            where5 = where4 + [('ressource_id','=',0)]
            dirids = dirobj.search(cr,uid, where5)            
            where5 = where4 + [('ressource_id','=',self.res_id)]
            dirids = dirids + dirobj.search(cr,uid, where5)            
            for dirr in dirobj.browse(cr, uid, dirids, context=ctx):
                if dirr.type == 'directory' and not dirr.parent_id:
                    res.append(node_res_obj(dirr.name, dirr.id, self, self.context, self.res_model, res_bo = None, res_id = self.res_id))
                if dirr.type == 'ressource':
                    res.append(node_res_dir(dirr.name, self, self.context, dirr, {'active_id': self.res_id}))                
        return res

    def create_child_collection(self, cr, objname):
        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        res_obj = dirobj.pool.get(self.context.context['res_model'])           
        
        object2 = res_obj.browse(cr, uid, self.context.context['res_id']) or False            
        
        obj = dirobj.browse(cr, uid, self.dir_id)            
        if obj and (obj.type == 'ressource') and not object2:
            raise OSError(1, 'Operation not permited.')

        
        val = {
                'name': objname,
                'ressource_parent_type_id': obj and obj.ressource_type_id.id or False,
                'ressource_id': object2 and object2.id or False,
                'parent_id' : False
        }        
        if (obj and (obj.type in ('directory'))) or not object2:                
            val['parent_id'] =  obj and obj.id or False            
        
        return dirobj.create(cr, uid, val)
    
    def create_child(self,cr,path,data):
        """ API function to create a child file object and node
            Return the node_* created
        """
        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        fil_obj=dirobj.pool.get('ir.attachment')
        val = {
            'name': path,
            'datas_fname': path,
            'parent_id': self.dir_id,
            'res_model': self.res_model,
            'res_id': self.res_id,
            # Datas are not set here
        }

        fil_id = fil_obj.create(cr,uid, val, context=ctx)
        fil = fil_obj.browse(cr,uid,fil_id,context=ctx)
        fnode = node_file(path,self,self.context,fil)
        fnode.set_data(cr,data,fil)
        return fnode

    def _get_ttag(self,cr):
        return 'rodir-%d-%d' % (self.dir_id,self.res_id)

class node_file(node_class):
    our_type = 'file'
    def __init__(self,path, parent, context, fil):
        super(node_file,self).__init__(path, parent,context)
        self.file_id = fil.id
        #todo: more info from ir_attachment
        if fil.file_type and '/' in fil.file_type:
            self.mimetype = fil.file_type
        self.create_date = fil.create_date
        self.write_date = fil.write_date or fil.create_date
        self.content_length = fil.file_size
        self.displayname = fil.name
        
        # This only propagates the problem to get_data. Better
        # fix those files to point to the root dir.
        if fil.parent_id:
            self.storage_id = fil.parent_id.storage_id.id
        else:
            self.storage_id = None    

    def open(self, cr, mode=False):
        uid = self.context.uid
        if self.type in ('collection','database'):
            return False            
        fobj = self.context._dirobj.pool.get('ir.attachment').browse(cr, uid, self.file_id, context=self.context.context)
        if fobj.store_method and fobj.store_method== 'fs' :
            s = StringIO.StringIO(self.get_data(cr, fobj))
        else:
            s = StringIO.StringIO(base64.decodestring(fobj.db_datas or ''))
        s.name = self
        return s                   

    def fix_ppath(self, cr, fbro):
        """Sometimes we may init this w/o path, parent.
        This function fills the missing path from the file browse object
        
        Note: this may be an expensive operation, do on demand. However,
        once caching is in, we might want to do that at init time and keep
        this object anyway
        """
        if self.path or self.parent:
            return
        assert fbro
        uid = self.context.uid
        
        dirpath = []
        if fbro.parent_id:
            dirobj = self.context._dirobj.pool.get('document.directory')
            dirpath = dirobj.get_full_path(cr, uid, fbro.parent_id.id, context=self.context.context)
        if fbro.datas_fname:
            dirpath.append(fbro.datas_fname)
        else:
            dirpath.append(fbro.name)
        
        if len(dirpath)>1:
            self.path = dirpath
        else:
            self.path = dirpath[0]   
    
    def get_data(self, cr, fil_obj = None):
        """ Retrieve the data for some file. 
            fil_obj may optionally be specified, and should be a browse object
            for the file. This is useful when the caller has already initiated
            the browse object. """
        # this is where storage kicks in..
        stor = self.storage_id
        if not stor:
            data_obj = self.context._dirobj.pool.get('ir.model.data')
            data_id = data_obj._get_id(cr, self.context.uid, 'document', 'storage_db')
            if data_id:
                stor = data_obj.browse(cr, self.context.uid, data_id, context=self.context.context).res_id 
        assert stor
        stobj = self.context._dirobj.pool.get('document.storage')
        return stobj.get_data(cr,self.context.uid,stor, self,self.context.context, fil_obj)

    def get_data_len(self, cr, fil_obj = None):
        # TODO: verify with the storage object!
        bin_size = self.context.context.get('bin_size', False)
        if bin_size and not self.content_length:
            self.content_length = fil_obj.db_datas
        return self.content_length

    def set_data(self, cr, data, fil_obj = None):
        """ Store data at some file. 
            fil_obj may optionally be specified, and should be a browse object
            for the file. This is useful when the caller has already initiated
            the browse object. """
        # this is where storage kicks in..
        stor = self.storage_id
        if not stor:
            data_obj = self.context._dirobj.pool.get('ir.model.data')
            data_id = data_obj._get_id(cr, self.context.uid, 'document', 'storage_db')
            if data_id:
                stor = data_obj.browse(cr, self.context.uid, data_id, context=self.context.context).res_id 
        assert stor
        stobj = self.context._dirobj.pool.get('document.storage')
        return stobj.set_data(cr,self.context.uid,stor, self, data, self.context.context, fil_obj)

    def _get_ttag(self,cr):
        return 'file-%d' % self.file_id

class node_content(node_class):
    our_type = 'content'
    def __init__(self,path, parent, context, cnt, dctx = None, act_id=None):
        super(node_content,self).__init__(path, parent,context)
        self.cnt_id = cnt.id
        self.create_date = False
        self.write_date = False
        self.content_length = False
        self.extension = cnt.extension
        self.report_id = cnt.report_id and cnt.report_id.id
        #self.mimetype = cnt.extension.
        self.displayname = path
        if dctx:
           self.dctx.update(dctx)
        self.act_id = act_id

    def open(self, cr, mode=False):
        uid = self.context.uid
        if self.type in ('collection','database'):
            return False                    
        pool = self.context._dirobj.pool
        res = getattr(pool.get('document.directory.content'), 'process_read')(cr, uid, self)
        res = StringIO.StringIO(res)
        res.name = self
        return res     
    
    def fill_fields(self,cr,dctx = None):
        """ Try to read the object and fill missing fields, like mimetype,
            dates etc.
            This function must be different from the constructor, because
            it uses the db cursor.
        """
        
        cr.execute('SELECT DISTINCT mimetype FROM document_directory_content_type WHERE active AND code = %s;',
                (self.extension,))
        res = cr.fetchall()
        if res and res[0][0]:
            self.mimetype = res[0][0]


    def get_data(self, cr, fil_obj = None):
        cntobj = self.context._dirobj.pool.get('document.directory.content')
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        data = cntobj.process_read(cr,self.context.uid,self,ctx)
        if data:
            self.content_length = len(data)
        return data

    def get_data_len(self, cr, fil_obj = None):
        if not self.content_length:
            self.get_data(cr,fil_obj)
        return self.content_length

    def set_data(self, cr, data, fil_obj = None):
        cntobj = self.context._dirobj.pool.get('document.directory.content')
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        return cntobj.process_write(cr,self.context.uid,self, data,ctx)

    def _get_ttag(self,cr):
        return 'cnt-%d%s' % (self.cnt_id,(self.act_id and ('-' + str(self.act_id))) or '')
