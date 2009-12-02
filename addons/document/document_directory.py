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

import base64

from osv import osv, fields
from osv.orm import except_orm
import urlparse

import os
import nodes

class document_directory(osv.osv):
    _name = 'document.directory'
    _description = 'Document directory'
    _columns = {
        'name': fields.char('Name', size=64, required=True, select=1),
        'write_date': fields.datetime('Date Modified', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True),
        'create_date': fields.datetime('Date Created', readonly=True),
        'create_uid':  fields.many2one('res.users', 'Creator', readonly=True),
        'file_type': fields.char('Content Type', size=32),
        'domain': fields.char('Domain', size=128, help="Use a domain if you want to apply an automatic filter on visible resources."),
        'user_id': fields.many2one('res.users', 'Owner'),
	'storage_id': fields.many2one('document.storage', 'Storage'),
        'group_ids': fields.many2many('res.groups', 'document_directory_group_rel', 'item_id', 'group_id', 'Groups'),
        'parent_id': fields.many2one('document.directory', 'Parent Item'),
        'child_ids': fields.one2many('document.directory', 'parent_id', 'Children'),
        'file_ids': fields.one2many('ir.attachment', 'parent_id', 'Files'),
        'content_ids': fields.one2many('document.directory.content', 'directory_id', 'Virtual Files'),
        'type': fields.selection([('directory','Static Directory'),('ressource','Other Resources')], 'Type', required=True),
        'ressource_type_id': fields.many2one('ir.model', 'Directories Mapped to Objects',
            help="Select an object here and Open ERP will create a mapping for each of these " \
                 "objects, using the given domain, when browsing through FTP."),
        'resource_field': fields.char('Name field',size=32,help='Field to be used as name on resource directories. If empty, the "name" will be used.'),
        'ressource_parent_type_id': fields.many2one('ir.model', 'Parent Model',
            help="If you put an object here, this directory template will appear bellow all of these objects. " \
                 "Don't put a parent directory if you select a parent model."),
        'ressource_id': fields.integer('Resource ID'),
        'ressource_tree': fields.boolean('Tree Structure',
            help="Check this if you want to use the same tree structure as the object selected in the system."),
        'dctx_ids': fields.one2many('document.directory.dctx', 'dir_id', 'Context fields'),
    }
    def _get_root_directory(self, cr,uid, context=None):
        objid=self.pool.get('ir.model.data')
        try:
            mid = objid._get_id(cr, uid, 'document', 'dir_root')
            if not mid:
                return None
        except Exception, e:
            import netsvc
            logger = netsvc.Logger()
            logger.notifyChannel("document", netsvc.LOG_WARNING, 'Cannot set directory root:'+ str(e))
            return None
        return objid.browse(cr, uid, mid, context=context).res_id

    def _get_def_storage(self,cr,uid,context=None):
        if context and context.has_key('default_parent_id'):
                # Use the same storage as the parent..
                diro = self.browse(cr,uid,context['default_parent_id'])
                if diro.storage_id:
                        return diro.storage_id.id
        objid=self.pool.get('ir.model.data')
        try:
                mid =  objid._get_id(cr, uid, 'document', 'storage_default')
                return objid.browse(cr, uid, mid, context=context).res_id
        except Exception:
                return None
        
    _defaults = {
        'user_id': lambda self,cr,uid,ctx: uid,
        'domain': lambda self,cr,uid,ctx: '[]',
        'type': lambda *args: 'directory',
        'ressource_id': lambda *a: 0,
        'parent_id': _get_root_directory,
        'storage_id': _get_def_storage,
    }
    _sql_constraints = [
        ('dirname_uniq', 'unique (name,parent_id,ressource_id,ressource_parent_type_id)', 'The directory name must be unique !'),
        ('no_selfparent', 'check(parent_id <> id)', 'Directory cannot be parent of itself!')
    ]

    def ol_get_resource_path(self,cr,uid,dir_id,res_model,res_id):
        # this method will be used in process module
        # to be need test and Improvement if resource dir has parent resource (link resource)
        path=[]
        def _parent(dir_id,path):
            parent=self.browse(cr,uid,dir_id)
            if parent.parent_id and not parent.ressource_parent_type_id:
                _parent(parent.parent_id.id,path)
                path.append(parent.name)
            else:
                path.append(parent.name)
                return path

        directory=self.browse(cr,uid,dir_id)
        model_ids=self.pool.get('ir.model').search(cr,uid,[('model','=',res_model)])
        if directory:
            _parent(dir_id,path)
            path.append(self.pool.get(directory.ressource_type_id.model).browse(cr,uid,res_id).name)
            #user=self.pool.get('res.users').browse(cr,uid,uid)
            #return "ftp://%s:%s@localhost:%s/%s/%s"%(user.login,user.password,config.get('ftp_server_port',8021),cr.dbname,'/'.join(path))
	    # No way we will return the password!
	    return "ftp://user:pass@host:port/test/this"
        return False

    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute('select distinct parent_id from document_directory where id in ('+','.join(map(str,ids))+')')
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, 'Error! You can not create recursive Directories.', ['parent_id'])
    ]
    def __init__(self, *args, **kwargs):
        res = super(document_directory, self).__init__(*args, **kwargs)
        #self._cache = {}

    def onchange_content_id(self, cr, uid, ids, ressource_type_id):
        return {}

    """
        PRE:
            uri: of the form "Sales Order/SO001"
        PORT:
            uri
            object: the object.directory or object.directory.content
            object2: the other object linked (if object.directory.content)
    """
    def get_object(self, cr, uid, uri, context=None):
        """ Return a node object for the given uri.
           This fn merely passes the call to node_context
        """
        if not context:
                context = {}
        lang = context.get('lang',False)
        if not lang:
            user = self.pool.get('res.users').browse(cr, uid, uid)
            lang = user.context_lang 
            context['lang'] = lang
            
        try: #just instrumentation
                return nodes.get_node_context(cr, uid, context).get_uri(cr,uri)
        except Exception,e:
                print "exception: ",e
                raise


    def _locate_child(self, cr,uid, root_id, uri,nparent, ncontext):
        """ try to locate the node in uri,
            Return a tuple (node_dir, remaining_path)
        """
        did = root_id
        duri = uri
        path = []
        context = ncontext.context
        while len(duri):
            nid = self.search(cr,uid,[('parent_id','=',did),('name','=',duri[0]),('type','=','directory')], context=context)
            if not nid:
                break
            if len(nid)>1:
                print "Duplicate dir? p= %d, n=\"%s\"" %(did,duri[0])
            path.append(duri[0])
            duri = duri[1:]
            did = nid[0]
        
        return (nodes.node_dir(path, nparent,ncontext,self.browse(cr,uid,did, context)), duri)

        
        nid = self.search(cr,uid,[('parent_id','=',did),('name','=',duri[0]),('type','=','ressource')], context=context)
        if nid:
            if len(nid)>1:
                print "Duplicate dir? p= %d, n=\"%s\"" %(did,duri[0])
            path.append(duri[0])
            duri = duri[1:]
            did = nid[0]
            return nodes.node_res_dir(path, nparent,ncontext,self.browse(cr,uid,did, context))

        # Here, we must find the appropriate non-dir child..
        # Chech for files:
        fil_obj = self.pool.get('ir.attachment')
        nid = fil_obj.search(cr,uid,[('parent_id','=',did),('name','=',duri[0])],context=context)
        if nid:
                if len(duri)>1:
                        # cannot treat child as a dir
                        return None
                if len(nid)>1:
                        print "Duplicate file?",did,duri[0]
                path.append(duri[0])
                return nodes.node_file(path,nparent,ncontext,fil_obj.browse(cr,uid,nid[0],context))
        
        print "nothing found:",did, duri
        #still, nothing found
        return None
        
    def old_code():
        if not uri:
            return node_database(cr, uid, context=context)
        turi = tuple(uri)
        node = node_class(cr, uid, '/', False, context=context, type='database')
        for path in uri[:]:
            if path:
                node = node.child(path)
                if not node:
                    return False
        oo = node.object and (node.object._name, node.object.id) or False
        oo2 = node.object2 and (node.object2._name, node.object2.id) or False
        return node

    def ol_get_childs(self, cr, uid, uri, context={}):
        node = self.get_object(cr, uid, uri, context)
        if uri:
            children = node.children()
        else:
            children= [node]
        result = map(lambda node: node.path_get(), children)
        return result

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default ={}
        name = self.read(cr, uid, [id])[0]['name']
        default.update({'name': name+ " (copy)"})
        return super(document_directory,self).copy(cr,uid,id,default,context)

    def _check_duplication(self, cr, uid,vals,ids=[],op='create'):
        name=vals.get('name',False)
        parent_id=vals.get('parent_id',False)
        ressource_parent_type_id=vals.get('ressource_parent_type_id',False)
        ressource_id=vals.get('ressource_id',0)
        if op=='write':
            for directory in self.browse(cr,uid,ids):
                if not name:
                    name=directory.name
                if not parent_id:
                    parent_id=directory.parent_id and directory.parent_id.id or False
                if not ressource_parent_type_id:
                    ressource_parent_type_id=directory.ressource_parent_type_id and directory.ressource_parent_type_id.id or False
                if not ressource_id:
                    ressource_id=directory.ressource_id and directory.ressource_id or 0
                res=self.search(cr,uid,[('id','<>',directory.id),('name','=',name),('parent_id','=',parent_id),('ressource_parent_type_id','=',ressource_parent_type_id),('ressource_id','=',ressource_id)])
                if len(res):
                    return False
        if op=='create':
            res=self.search(cr,uid,[('name','=',name),('parent_id','=',parent_id),('ressource_parent_type_id','=',ressource_parent_type_id),('ressource_id','=',ressource_id)])
            if len(res):
                return False
        return True
    def write(self, cr, uid, ids, vals, context=None):
        if not self._check_duplication(cr,uid,vals,ids,op='write'):
            raise osv.except_osv(_('ValidateError'), _('Directory name must be unique!'))
        return super(document_directory,self).write(cr,uid,ids,vals,context=context)

    def create(self, cr, uid, vals, context=None):
        if not self._check_duplication(cr,uid,vals):
            raise osv.except_osv(_('ValidateError'), _('Directory name must be unique!'))
        if vals.get('name',False) and (vals.get('name').find('/')+1 or vals.get('name').find('@')+1 or vals.get('name').find('$')+1 or vals.get('name').find('#')+1) :
            raise osv.except_osv(_('ValidateError'), _('Directory name contains special characters!'))
        return super(document_directory,self).create(cr, uid, vals, context)

document_directory()

class document_directory_dctx(osv.osv):
    """ In order to evaluate dynamic folders, child items could have a limiting
        domain expression. For that, their parents will export a context where useful
        information will be passed on.
        If you define sth like "s_id" = "this.id" at a folder iterating over sales, its
        children could have a domain like [('sale_id', = ,dctx_s_id )]
        This system should be used recursively, that is, parent dynamic context will be
        appended to all children down the tree.
    """
    _name = 'document.directory.dctx'
    _description = 'Directory dynamic context'
    _columns = {
        'dir_id': fields.many2one('document.directory', 'Directory', required=True),
        'field': fields.char('Field', size=20, required=True, select=1, help="The name of the field. Note that the prefix \"dctx_\" will be prepended to what is typed here."),
        'expr': fields.char('Expression', size=64, required=True, help="A python expression used to evaluate the field.\n" + \
                "You can use 'dir_id' for current dir, 'res_id', 'res_model' as a reference to the current record, in dynamic folders"),
        }

document_directory_dctx()


class document_directory_node(osv.osv):
    _inherit = 'process.node'
    _columns = {
        'directory_id':  fields.many2one('document.directory', 'Document directory', ondelete="set null"),
    }
document_directory_node()
