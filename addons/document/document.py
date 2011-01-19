# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import base64
import os
import urlparse
import StringIO
import random
import string
from psycopg2 import Binary

import tools
from tools.translate import _
from tools import config
from tools.safe_eval import safe_eval as eval

from osv import osv, fields
from osv.orm import except_orm

import pooler
import netsvc

from content_index import content_index

def random_name():
    random.seed()
    d = [random.choice(string.ascii_letters) for x in xrange(10) ]
    name = "".join(d)
    return name


# Unsupported WebDAV Commands:
#     label
#     search
#     checkin
#     checkout
#     propget
#     propset

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
INVALID_CHARS={'*':str(hash('*')), '|':str(hash('|')) , "\\":str(hash("\\")), '/':'__', ':':str(hash(':')), '"':str(hash('"')), '<':str(hash('<')) , '>':str(hash('>')) , '?':str(hash('?'))}


class node_class(object):
    def __init__(self, cr, uid, path, object, object2=False, context=None, content=False, type='collection', root=False):
        self.cr = cr
        self.uid = uid
        self.path = path
        self.object = object
        self.object2 = object2
        self.context = context
        if self.context is None:
            self.context = {}
        self.content = content
        self.type=type
        self.root=root

    def _file_get(self, nodename=False):
        if not self.object:
            return []
        pool = pooler.get_pool(self.cr.dbname)
        fobj = pool.get('ir.attachment')
        res2 = []
        where = []
        if self.object2:
            where.append( ('res_model','=',self.object2._name) )
            where.append( ('res_id','=',self.object2.id) )
        else:
            where.append( ('parent_id','=',self.object.id) )
            where.append( ('res_id','=',False) )
        if nodename:
            where.append( (fobj._rec_name,'=',nodename) )
        for content in self.object.content_ids:
            if self.object2 or not content.include_name:
                if content.include_name:
                    content_name = self.object2.name
                    obj = pool.get(self.object.ressource_type_id.model)
                    name_for = obj._name.split('.')[-1]
                    if content_name  and content_name.find(name_for) == 0  :
                        content_name = content_name.replace(name_for,'')
                    test_nodename = content_name + (content.suffix or '') + (content.extension or '')
                else:
                    test_nodename = (content.suffix or '') + (content.extension or '')
                if test_nodename.find('/'):
                    test_nodename=test_nodename.replace('/', '_')
                path = self.path+'/'+test_nodename
                if not nodename:
                    n = node_class(self.cr, self.uid,path, self.object2, False, context=self.context, content=content, type='content', root=False)
                    res2.append( n)
                else:
                    if nodename == test_nodename:
                        n = node_class(self.cr, self.uid, path, self.object2, False, context=self.context, content=content, type='content', root=False)
                        res2.append(n)

        ids = fobj.search(self.cr, self.uid, where+[ ('parent_id','=',self.object and self.object.id or False) ])
        if self.object and self.root and (self.object.type=='ressource'):
            ids += fobj.search(self.cr, self.uid, where+[ ('parent_id','=',False) ])
        res = fobj.browse(self.cr, self.uid, ids, context=self.context)
        return map(lambda x: node_class(self.cr, self.uid, self.path+'/'+eval('x.'+fobj._rec_name, {'x' : x}), x, False, context=self.context, type='file', root=False), res) + res2

    def get_translation(self,value,lang):
        result = value
        #TODO : to get translation term
        return result

    def directory_list_for_child(self,nodename,parent=False):
        pool = pooler.get_pool(self.cr.dbname)
        where = []
        if nodename:
            nodename = self.get_translation(nodename, self.context['lang'])
            where.append(('name','=',nodename))
        if (self.object and self.object.type=='directory') or not self.object2:
            where.append(('parent_id','=',self.object and self.object.id or False))
        else:
            where.append(('parent_id','=',False))
        if self.object:
            where.append(('ressource_parent_type_id','=',self.object.ressource_type_id.id))
        else:
            where.append(('ressource_parent_type_id','=',False))

        ids = pool.get('document.directory').search(self.cr, self.uid, where+[('ressource_id','=',0)])
        if self.object2:
            ids += pool.get('document.directory').search(self.cr, self.uid, where+[('ressource_id','=',self.object2.id)])
        res = pool.get('document.directory').browse(self.cr, self.uid, ids, self.context)
        return res

    def _child_get(self, nodename=False):
        if self.type not in ('collection','database'):
            return []
        res = self.directory_list_for_child(nodename)
        result= map(lambda x: node_class(self.cr, self.uid, self.path+'/'+x.name, x, x.type=='directory' and self.object2 or False, context=self.context, root=self.root), res)
        if self.type=='database':
            pool = pooler.get_pool(self.cr.dbname)
            fobj = pool.get('ir.attachment')
            vargs = [('parent_id','=',False),('res_id','=',False)]
            if nodename:
                vargs.append((fobj._rec_name,'=',nodename))
            file_ids=fobj.search(self.cr,self.uid,vargs)

            res = fobj.browse(self.cr, self.uid, file_ids, context=self.context)
            result +=map(lambda x: node_class(self.cr, self.uid, self.path+'/'+eval('x.'+fobj._rec_name, {'x' : x}), x, False, context=self.context, type='file', root=self.root), res)
        if self.type=='collection' and self.object.type=="ressource":
            where = self.object.domain and eval(self.object.domain, {'active_id':self.root, 'uid':self.uid}) or []
            pool = pooler.get_pool(self.cr.dbname)
            obj = pool.get(self.object.ressource_type_id.model)
            _dirname_field = obj._rec_name
            if len(obj.fields_get(self.cr, self.uid, ['dirname'])):
                _dirname_field = 'dirname'

            name_for = obj._name.split('.')[-1]
            if nodename  and nodename.find(name_for) == 0  :
                id = int(nodename.replace(name_for,''))
                where.append(('id','=',id))
            elif nodename:
                if nodename.find('__') :
                    nodename=nodename.replace('__','/')
                for invalid in INVALID_CHARS:
                    if nodename.find(INVALID_CHARS[invalid]) :
                        nodename=nodename.replace(INVALID_CHARS[invalid],invalid)
                nodename = self.get_translation(nodename, self.context['lang'])
                where.append((_dirname_field,'=',nodename))

            if self.object.ressource_tree:
                if obj._parent_name in obj.fields_get(self.cr,self.uid):
                    where.append((obj._parent_name,'=',self.object2 and self.object2.id or False))
                    ids = obj.search(self.cr, self.uid, where)
                    res = obj.browse(self.cr, self.uid, ids,self.context)
                    result+= map(lambda x: node_class(self.cr, self.uid, self.path+'/'+x.name.replace('/','__'), self.object, x, context=self.context, root=x.id), res)
                    return result
                else :
                    if self.object2:
                        return result
            else:
                if self.object2:
                    return result


            ids = obj.search(self.cr, self.uid, where)
            res = obj.browse(self.cr, self.uid, ids,self.context)
            for r in res:
                if len(obj.fields_get(self.cr, self.uid, [_dirname_field])):
                    r.name = eval('r.'+_dirname_field, {'r' : r})
                else:
                    r.name = False
                if not r.name:
                    r.name = name_for + '%d'%r.id
                for invalid in INVALID_CHARS:
                    if r.name.find(invalid) :
                        r.name = r.name.replace(invalid,INVALID_CHARS[invalid])
            result2 = map(lambda x: node_class(self.cr, self.uid, self.path+'/'+x.name.replace('/','__'), self.object, x, context=self.context, root=x.id), res)
            if result2:
                if self.object.ressource_tree:
                    result += result2
                else:
                    result = result2
        return result

    def children(self):
        return self._child_get() + self._file_get()

    def child(self, name):
        res = self._child_get(name)
        if res:
            return res[0]
        res = self._file_get(name)
        if res:
            return res[0]
        return None

    def path_get(self):
        path = self.path
        if self.path[0]=='/':
            path = self.path[1:]
        return path

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
        'group_ids': fields.many2many('res.groups', 'document_directory_group_rel', 'item_id', 'group_id', 'Groups'),
        'parent_id': fields.many2one('document.directory', 'Parent Item'),
        'child_ids': fields.one2many('document.directory', 'parent_id', 'Children'),
        'file_ids': fields.one2many('ir.attachment', 'parent_id', 'Files'),
        'content_ids': fields.one2many('document.directory.content', 'directory_id', 'Virtual Files'),
        'type': fields.selection([('directory','Static Directory'),('ressource','Other Resources')], 'Type', required=True),
        'ressource_type_id': fields.many2one('ir.model', 'Directories Mapped to Objects',
            help="Select an object here and Open ERP will create a mapping for each of these " \
                 "objects, using the given domain, when browsing through FTP."),
        'ressource_parent_type_id': fields.many2one('ir.model', 'Parent Model',
            help="If you put an object here, this directory template will appear bellow all of these objects. " \
                 "Don't put a parent directory if you select a parent model."),
        'ressource_id': fields.integer('Resource ID'),
        'ressource_tree': fields.boolean('Tree Structure',
            help="Check this if you want to use the same tree structure as the object selected in the system."),
    }
    _defaults = {
        'user_id': lambda self,cr,uid,ctx: uid,
        'domain': lambda self,cr,uid,ctx: '[]',
        'type': lambda *args: 'directory',
        'ressource_id': lambda *a: 0
    }
    _sql_constraints = [
        ('dirname_uniq', 'unique (name,parent_id,ressource_id,ressource_parent_type_id)', 'The directory name must be unique !')
    ]

    def get_resource_path(self,cr,uid,dir_id,res_model,res_id):
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
            if res_id:
                path.append(self.pool.get(directory.ressource_type_id.model).browse(cr,uid,res_id).name)
            user=self.pool.get('res.users').browse(cr,uid,uid)
            return "ftp://%s:%s@localhost:%s/%s/%s"%(user.login,user.password,config.get('ftp_server_port',8021),cr.dbname,'/'.join(path))
        return False

    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute('SELECT DISTINCT parent_id FROM document_directory '\
                       'WHERE id in %s', (tuple(ids),))
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
        self._cache = {}

    def onchange_content_id(self, cr, uid, ids, ressource_type_id):
        return {}

    def _get_childs(self, cr, uid, node, nodename=False, context=None):
        where = []
        if nodename:
            nodename = self.get_translation(nodename, self.context['lang'])
            where.append(('name','=',nodename))
        if object:
            where.append(('parent_id','=',object.id))
        ids = self.search(cr, uid, where, context)
        return self.browse(cr, uid, ids, context), False

    """
        PRE:
            uri: of the form "Sales Order/SO001"
        PORT:
            uri
            object: the object.directory or object.directory.content
            object2: the other object linked (if object.directory.content)
    """
    def get_object(self, cr, uid, uri, context=None):
        if context is None:
            context = {}
        #TODO : set user's context_lang in context
        context.update({'lang':False})
        if not uri:
            return node_class(cr, uid, '', False, context=context, type='database')
        turi = tuple(uri)
        if False and (turi in self._cache):
            (path, oo, oo2, context, content,type,root) = self._cache[turi]
            if oo:
                object = self.pool.get(oo[0]).browse(cr, uid, oo[1], context)
            else:
                object = False
            if oo2:
                object2 = self.pool.get(oo2[0]).browse(cr, uid, oo2[1], context)
            else:
                object2 = False
            node = node_class(cr, uid, '/', False, context=context, type='database')
            return node

        node = node_class(cr, uid, '/', False, context=context, type='database')
        for path in uri[:]:
            if path:
                node = node.child(path)
                if not node:
                    return False
        oo = node.object and (node.object._name, node.object.id) or False
        oo2 = node.object2 and (node.object2._name, node.object2.id) or False
        self._cache[turi] = (node.path, oo, oo2, node.context, node.content,node.type,node.root)
        return node

    def get_childs(self, cr, uid, uri, context=None):
        node = self.get_object(cr, uid, uri, context)
        if uri:
            children = node.children()
        else:
            children= [node]
        result = map(lambda node: node.path_get(), children)
        #childs,object2 = self._get_childs(cr, uid, object, False, context)
        #result = map(lambda x: urlparse.urljoin(path+'/',x.name), childs)
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

class document_directory_node(osv.osv):
    _inherit = 'process.node'
    _columns = {
        'directory_id':  fields.many2one('document.directory', 'Document directory', ondelete="set null"),
    }
document_directory_node()

class document_directory_content_type(osv.osv):
    _name = 'document.directory.content.type'
    _description = 'Directory Content Type'
    _columns = {
        'name': fields.char('Content Type', size=64, required=True),
        'code': fields.char('Extension', size=4),
        'active': fields.boolean('Active'),
    }
    _defaults = {
        'active': lambda *args: 1
    }
document_directory_content_type()

class document_directory_content(osv.osv):
    _name = 'document.directory.content'
    _description = 'Directory Content'
    _order = "sequence"
    def _extension_get(self, cr, uid, context=None):
        cr.execute('select code,name from document_directory_content_type where active')
        res = cr.fetchall()
        return res
    _columns = {
        'name': fields.char('Content Name', size=64, required=True),
        'sequence': fields.integer('Sequence', size=16),
        'suffix': fields.char('Suffix', size=16),
        'report_id': fields.many2one('ir.actions.report.xml', 'Report'),
        'extension': fields.selection(_extension_get, 'Document Type', required=True, size=4),
        'include_name': fields.boolean('Include Record Name', help="Check this field if you want that the name of the file start by the record name."),
        'directory_id': fields.many2one('document.directory', 'Directory'),
    }
    _defaults = {
        'extension': lambda *args: '.pdf',
        'sequence': lambda *args: 1,
        'include_name': lambda *args: 1,
    }
    def process_write_pdf(self, cr, uid, node, context=None):
        return True
    def process_read_pdf(self, cr, uid, node, context=None):
        report = self.pool.get('ir.actions.report.xml').browse(cr, uid, node.content.report_id.id)
        srv = netsvc.LocalService('report.'+report.report_name)
        pdf,pdftype = srv.create(cr, uid, [node.object.id], {}, {})
        s = StringIO.StringIO(pdf)
        s.name = node
        return s
document_directory_content()

class ir_action_report_xml(osv.osv):
    _name="ir.actions.report.xml"
    _inherit ="ir.actions.report.xml"

    def _model_get(self, cr, uid, ids, name, arg, context):
        res = {}
        model_pool = self.pool.get('ir.model')
        for data in self.read(cr,uid,ids,['model']):
            model = data.get('model',False)
            if model:
                model_id =model_pool.search(cr,uid,[('model','=',model)])
                if model_id:
                    res[data.get('id')] = model_id[0]
                else:
                    res[data.get('id')] = False
        return res

    def _model_search(self, cr, uid, obj, name, args, context):
        if not len(args):
            return []
        model_id= args[0][2]
        if not model_id:
            return []
        model = self.pool.get('ir.model').read(cr,uid,[model_id])[0]['model']
        report_id = self.search(cr,uid,[('model','=',model)])
        if not report_id:
            return [('id','=','0')]
        return [('id','in',report_id)]

    _columns={
        'model_id' : fields.function(_model_get,fnct_search=_model_search,method=True,string='Model Id'),
    }

ir_action_report_xml()

def create_directory(path):
    dir_name = random_name()
    path = os.path.join(path,dir_name)
    os.makedirs(path)
    return dir_name

class document_file(osv.osv):
    _inherit = 'ir.attachment'
    _rec_name = 'datas_fname'
    def _get_filestore(self, cr):
        return os.path.join(tools.config['root_path'], 'filestore', cr.dbname)

    def _data_get(self, cr, uid, ids, name, arg, context):
        result = {}
        cr.execute('SELECT id, store_fname, link FROM ir_attachment '\
                   'WHERE id IN %s', (tuple(ids),))
        for id,r,l in cr.fetchall():
            try:
                value = file(os.path.join(self._get_filestore(cr), r), 'rb').read()
                result[id] = base64.encodestring(value)
            except:
                result[id]=''
#            if context.get('bin_size', False):
#                result[id] = tools.human_size(result[id])
        return result

    #
    # This code can be improved
    #
    def _data_set(self, cr, uid, id, name, value, args=None, context=None):
        if not value:
            filename = self.browse(cr, uid, id, context).store_fname
            try:
                os.unlink(os.path.join(self._get_filestore(cr), filename))
            except:
                pass
            cr.execute('update ir_attachment set store_fname=NULL WHERE id=%s', (id,) )
            return True
        #if (not context) or context.get('store_method','fs')=='fs':
        try:
            path = self._get_filestore(cr)
            if not os.path.isdir(path):
                try:
                    os.makedirs(path)
                except:
                    raise except_orm(_('Permission Denied !'), _('You do not permissions to write on the server side.'))

            flag = None
            # This can be improved
            for dirs in os.listdir(path):
                if os.path.isdir(os.path.join(path,dirs)) and len(os.listdir(os.path.join(path,dirs)))<4000:
                    flag = dirs
                    break
            flag = flag or create_directory(path)
            filename = random_name()
            fname = os.path.join(path, flag, filename)
            fp = file(fname,'wb')
            v = base64.decodestring(value)
            fp.write(v)
            filesize = os.stat(fname).st_size
            cr.execute('update ir_attachment set store_fname=%s,store_method=%s,file_size=%s where id=%s', (os.path.join(flag,filename),'fs',len(v),id))
            return True
        except Exception,e :
            raise except_orm(_('Error!'), str(e))

    _columns = {
        'user_id': fields.many2one('res.users', 'Owner', select=1),
        'group_ids': fields.many2many('res.groups', 'document_group_rel', 'item_id', 'group_id', 'Groups'),
        'parent_id': fields.many2one('document.directory', 'Directory', select=1),
        'file_size': fields.integer('File Size', required=True),
        'file_type': fields.char('Content Type', size=32),
        'index_content': fields.text('Indexed Content'),
        'write_date': fields.datetime('Date Modified', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True),
        'create_date': fields.datetime('Date Created', readonly=True),
        'create_uid':  fields.many2one('res.users', 'Creator', readonly=True),
        'store_method': fields.selection([('db','Database'),('fs','Filesystem'),('link','Link')], "Storing Method"),
        'datas': fields.function(_data_get,method=True,fnct_inv=_data_set,string='File Content',type="binary"),
        'store_fname': fields.char('Stored Filename', size=200),
        'res_model': fields.char('Attached Model', size=64), #res_model
        'res_id': fields.integer('Attached ID'), #res_id
        'partner_id':fields.many2one('res.partner', 'Partner', select=1),
        'title': fields.char('Resource Title',size=64),
    }

    _defaults = {
        'user_id': lambda self,cr,uid,ctx:uid,
        'file_size': lambda self,cr,uid,ctx:0,
        'store_method': lambda *args: 'db'
    }
    _sql_constraints = [
        ('filename_uniq', 'unique (name,parent_id,res_id,res_model)', 'The file name must be unique !')
    ]
    def _check_duplication(self, cr, uid,vals,ids=[],op='create'):
        name=vals.get('name',False)
        parent_id=vals.get('parent_id',False)
        res_model=vals.get('res_model',False)
        res_id=vals.get('res_id',0)
        if op=='write':
            for file in self.browse(cr,uid,ids):
                if not name:
                    name=file.name
                if not parent_id:
                    parent_id=file.parent_id and file.parent_id.id or False
                if not res_model:
                    res_model=file.res_model and file.res_model or False
                if not res_id:
                    res_id=file.res_id and file.res_id or 0
                res=self.search(cr,uid,[('id','<>',file.id),('name','=',name),('parent_id','=',parent_id),('res_model','=',res_model),('res_id','=',res_id)])
                if len(res):
                    return False
        if op=='create':
            res=self.search(cr,uid,[('name','=',name),('parent_id','=',parent_id),('res_id','=',res_id),('res_model','=',res_model)])
            if len(res):
                return False
        return True
    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default ={}
        name = self.read(cr, uid, [id])[0]['name']
        default.update({'name': name+ " (copy)"})
        return super(document_file,self).copy(cr,uid,id,default,context)
    def write(self, cr, uid, ids, vals, context=None):
        res=self.search(cr,uid,[('id','in',ids)])
        if not len(res):
            return False
        if not self._check_duplication(cr,uid,vals,ids,'write'):
            raise except_orm(_('ValidateError'), _('File name must be unique!'))
        result = super(document_file,self).write(cr,uid,ids,vals,context=context)
        cr.commit()
        try:
            for f in self.browse(cr, uid, ids, context=context):
                #if 'datas' not in vals:
                #    vals['datas']=f.datas
                res = content_index(base64.decodestring(vals['datas']), f.datas_fname, f.file_type or None)
                super(document_file,self).write(cr, uid, ids, {
                    'index_content': res
                })
            cr.commit()
        except:
            pass
        return result

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        vals['title']=vals['name']
        vals['parent_id'] = context.get('parent_id',False) or vals.get('parent_id',False)
        if not vals.get('res_id', False) and context.get('default_res_id',False):
            vals['res_id']=context.get('default_res_id',False)
        if not vals.get('res_model', False) and context.get('default_res_model',False):
            vals['res_model']=context.get('default_res_model',False)

        if vals.get('res_id', False) and vals.get('res_model',False):
            obj_model=self.pool.get(vals['res_model'])
            result = obj_model.read(cr, uid, [vals['res_id']], context=context)
            if len(result):
                obj=result[0]
                if obj.get('name',False):
                    vals['title'] = (obj.get('name',''))[:60]
                if obj_model._name=='res.partner':
                    vals['partner_id']=obj['id']
                elif obj.get('address_id',False):
                    if isinstance(obj['address_id'],tuple) or isinstance(obj['address_id'],list):
                        address_id=obj['address_id'][0]
                    else:
                        address_id=obj['address_id']
                    address=self.pool.get('res.partner.address').read(cr,uid,[address_id],context=context)
                    if len(address):
                        vals['partner_id']=address[0]['partner_id'][0] or False
                elif obj.get('partner_id',False):
                    if isinstance(obj['partner_id'],tuple) or isinstance(obj['partner_id'],list):
                        vals['partner_id']=obj['partner_id'][0]
                    else:
                        vals['partner_id']=obj['partner_id']

        datas=None
        if vals.get('link',False) :
            import urllib
            datas=base64.encodestring(urllib.urlopen(vals['link']).read())
        else:
            datas = vals.get('datas',False)

        vals['file_size']= datas and len(datas) or 0
        if not self._check_duplication(cr,uid,vals):
            raise except_orm(_('ValidateError'), _('File name must be unique!'))
        result = super(document_file,self).create(cr, uid, vals, context)
        cr.commit()
        try:
            res = content_index(base64.decodestring(datas), vals['datas_fname'], vals.get('content_type', None))
            super(document_file,self).write(cr, uid, [result], {
                'index_content' : res,
            })
            cr.commit()
        except:
            pass
        return result

    def unlink(self,cr, uid, ids, context=None):
        for f in self.browse(cr, uid, ids, context):
            #if f.store_method=='fs':
            try:
                os.unlink(os.path.join(self._get_filestore(cr), f.store_fname))
            except:
                pass
        return super(document_file, self).unlink(cr, uid, ids, context)
document_file()

class document_configuration_wizard(osv.osv_memory):
    _name='document.configuration.wizard'
    _rec_name = 'Auto Directory configuration'
    _columns = {
        'host': fields.char('Server Address', size=64, help="Put here the server address or IP. " \
            "Keep localhost if you don't know what to write.", required=True)
    }

    def detect_ip_addr(self, cr, uid, context=None):
        def _detect_ip_addr(self, cr, uid, context=None):
            from array import array
            import socket
            from struct import pack, unpack

            try:
                import fcntl
            except ImportError:
                fcntl = None

            if not fcntl: # not UNIX:
                host = socket.gethostname()
                ip_addr = socket.gethostbyname(host)
            else: # UNIX:
                # get all interfaces:
                nbytes = 128 * 32
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                names = array('B', '\0' * nbytes)
                outbytes = unpack('iL', fcntl.ioctl( s.fileno(), 0x8912, pack('iL', nbytes, names.buffer_info()[0])))[0]
                namestr = names.tostring()
                ifaces = [namestr[i:i+32].split('\0', 1)[0] for i in range(0, outbytes, 32)]

                for ifname in [iface for iface in ifaces if iface != 'lo']:
                    ip_addr = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, pack('256s', ifname[:15]))[20:24])
                    break
            return ip_addr

        try:
            ip_addr = _detect_ip_addr(self, cr, uid, context)
        except:
            ip_addr = 'localhost'
        return ip_addr

    _defaults = {
        'host': detect_ip_addr,
    }

    def action_cancel(self,cr,uid,ids,conect=None):
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
         }

    def action_config(self, cr, uid, ids, context=None):
        conf = self.browse(cr, uid, ids[0], context)
        obj=self.pool.get('document.directory')
        objid=self.pool.get('ir.model.data')

        if self.pool.get('sale.order'):
            id = objid._get_id(cr, uid, 'document', 'dir_sale_order_all')
            id = objid.browse(cr, uid, id, context=context).res_id
            mid = self.pool.get('ir.model').search(cr, uid, [('model','=','sale.order')])
            obj.write(cr, uid, [id], {
                'type':'ressource',
                'ressource_type_id': mid[0],
                'domain': '[]',
            })
            aid = objid._get_id(cr, uid, 'sale', 'report_sale_order')
            aid = objid.browse(cr, uid, aid, context=context).res_id

            self.pool.get('document.directory.content').create(cr, uid, {
                'name': "Print Order",
                'suffix': "_print",
                'report_id': aid,
                'extension': '.pdf',
                'include_name': 1,
                'directory_id': id,
            })
            id = objid._get_id(cr, uid, 'document', 'dir_sale_order_quote')
            id = objid.browse(cr, uid, id, context=context).res_id
            obj.write(cr, uid, [id], {
                'type':'ressource',
                'ressource_type_id': mid[0],
                'domain': "[('state','=','draft')]",
            })

        if self.pool.get('product.product'):
            id = objid._get_id(cr, uid, 'document', 'dir_product')
            id = objid.browse(cr, uid, id, context=context).res_id
            mid = self.pool.get('ir.model').search(cr, uid, [('model','=','product.product')])
            obj.write(cr, uid, [id], {
                'type':'ressource',
                'ressource_type_id': mid[0],
            })

        if self.pool.get('stock.location'):
            aid = objid._get_id(cr, uid, 'stock', 'report_product_history')
            aid = objid.browse(cr, uid, aid, context=context).res_id

            self.pool.get('document.directory.content').create(cr, uid, {
                'name': "Product Stock",
                'suffix': "_stock_forecast",
                'report_id': aid,
                'extension': '.pdf',
                'include_name': 1,
                'directory_id': id,
            })

        if self.pool.get('account.analytic.account'):
            id = objid._get_id(cr, uid, 'document', 'dir_project')
            id = objid.browse(cr, uid, id, context=context).res_id
            mid = self.pool.get('ir.model').search(cr, uid, [('model','=','account.analytic.account')])
            obj.write(cr, uid, [id], {
                'type':'ressource',
                'ressource_type_id': mid[0],
                'domain': '[]',
                'ressource_tree': 1
        })

        aid = objid._get_id(cr, uid, 'document', 'action_document_browse')
        aid = objid.browse(cr, uid, aid, context=context).res_id
        self.pool.get('ir.actions.url').write(cr, uid, [aid], {'url': 'ftp://'+(conf.host or 'localhost')+':8021/'})

        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
        }
document_configuration_wizard()
