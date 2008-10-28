# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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

import base64

from osv import osv, fields
from osv.orm import except_orm
import urlparse

import os

import pooler
from content_index import content_index

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
    def __init__(self, cr, uid, path,object,object2=False, context={}, content=False, type='collection', root=False):
        self.cr = cr
        self.uid = uid
        self.path = path
        self.object = object
        self.object2 = object2
        self.context = context
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
        print '_FILE_GET', nodename
        if self.object2:
            where.append( ('res_model','=',self.object2._name) )
            where.append( ('res_id','=',self.object2.id) )
        for content in self.object.content_ids:
            if self.object2 or not content.include_name:
                if content.include_name:
                    test_nodename = self.object2.name + (content.suffix or '') + (content.extension or '')
                else:
                    test_nodename = (content.suffix or '') + (content.extension or '')
                print 'TESTING CONTENT', test_nodename
                if test_nodename.find('/'):
                    test_nodename=test_nodename.replace('/', '_')
                path = self.path+'/'+test_nodename
                #path = self.path+'/'+self.object2.name + (content.suffix or '') + (content.extension or '')
                if not nodename:
                    n = node_class(self.cr, self.uid,path, self.object2, False, content=content, type='content', root=False)
                    res2.append( n)
                else:
                    if nodename == test_nodename:
                        n = node_class(self.cr, self.uid, path, self.object2, False, content=content, type='content', root=False)
                        res2.append(n)
        else:
            where.append( ('parent_id','=',self.object.id) )
            where.append( ('res_id','=',False) )
        if nodename:
            where.append( (fobj._rec_name,'=',nodename) )
        ids = fobj.search(self.cr, self.uid, where+[ ('parent_id','=',self.object and self.object.id or False) ], context=self.context)
        if self.object and self.root and (self.object.type=='ressource'):
            ids += fobj.search(self.cr, self.uid, where+[ ('parent_id','=',False) ], context=self.context)
        res = fobj.browse(self.cr, self.uid, ids, context=self.context)
        return map(lambda x: node_class(self.cr, self.uid, self.path+'/'+x.name, x, False, type='file', root=False), res) + res2

    def directory_list_for_child(self,nodename,parent=False):
        pool = pooler.get_pool(self.cr.dbname)
        where = []
        if nodename:
            where.append(('name','=',nodename))
        if (self.object and self.object.type=='directory') or not self.object2:
            where.append(('parent_id','=',self.object and self.object.id or False))
        else:
            where.append(('parent_id','=',False))
        if self.object:
            where.append(('ressource_parent_type_id','=',self.object.ressource_type_id.id))
        else:
            where.append(('ressource_parent_type_id','=',False))

        ids = pool.get('document.directory').search(self.cr, self.uid, where+[('ressource_id','=',0)], self.context)
        if self.object2:
            ids += pool.get('document.directory').search(self.cr, self.uid, where+[('ressource_id','=',self.object2.id)], self.context)
        res = pool.get('document.directory').browse(self.cr, self.uid, ids,self.context)
        return res

    def _child_get(self, nodename=False):
        print 'Getting Childs', nodename, self.type
        if self.type not in ('collection','database'):
            return []
        res = self.directory_list_for_child(nodename)
        result= map(lambda x: node_class(self.cr, self.uid, self.path+'/'+x.name, x, x.type=='directory' and self.object2 or False, root=self.root), res)
        print 'RESULT', result
        if self.type=='database':
            pool = pooler.get_pool(self.cr.dbname)
            fobj = pool.get('ir.attachment')
            vargs = [('parent_id','=',False),('res_id','=',False)]
            if nodename:
                vargs.append(('name','=',nodename))
            file_ids=fobj.search(self.cr,self.uid,vargs)

            res = fobj.browse(self.cr, self.uid, file_ids, context=self.context)
            result +=map(lambda x: node_class(self.cr, self.uid, self.path+'/'+x.name, x, False, type='file', root=self.root), res)
            print 'DATABASE', result
        if self.type=='collection' and self.object.type=="ressource":
            print 'ICI'
            where = self.object.domain and eval(self.object.domain, {'active_id':self.root}) or []
            pool = pooler.get_pool(self.cr.dbname)
            obj = pool.get(self.object.ressource_type_id.model)

            if self.object.ressource_tree:
                if obj._parent_name in obj.fields_get(self.cr,self.uid):
                    where.append((obj._parent_name,'=',self.object2 and self.object2.id or False))
                else :
                    if self.object2:
                        return result
            else:
                if self.object2:
                    return result

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
                where.append(('name','=',nodename))
            ids = obj.search(self.cr, self.uid, where, self.context)
            res = obj.browse(self.cr, self.uid, ids,self.context)
            for r in res:
                if not r.name:
                    r.name = name_for+'%d'%r.id
                for invalid in INVALID_CHARS:
                    if r.name.find(invalid) :
                        r.name=r.name.replace(invalid,INVALID_CHARS[invalid])
            result2 = map(lambda x: node_class(self.cr, self.uid, self.path+'/'+x.name.replace('/','__'), self.object, x, root=r.id), res)
            if result2:
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
        'domain': fields.char('Domain', size=128),
        'user_id': fields.many2one('res.users', 'Owner'),
        'group_ids': fields.many2many('res.groups', 'document_directory_group_rel', 'item_id', 'group_id', 'Groups'),
        'parent_id': fields.many2one('document.directory', 'Parent Item'),
        'child_ids': fields.one2many('document.directory', 'parent_id', 'Childs'),
        'file_ids': fields.one2many('ir.attachment', 'parent_id', 'Files'),
        'content_ids': fields.one2many('document.directory.content', 'directory_id', 'Virtual Files'),
        'type': fields.selection([('directory','Static Directory'),('ressource','Other Ressources')], 'Type', required=True),
        'ressource_type_id': fields.many2one('ir.model', 'Childs Model'),
        'ressource_parent_type_id': fields.many2one('ir.model', 'Linked Model'),
        'ressource_id': fields.integer('Ressource ID'),
        'ressource_tree': fields.boolean('Tree Structure'),
    }
    _defaults = {
        'user_id': lambda self,cr,uid,ctx: uid,
        'domain': lambda self,cr,uid,ctx: '[]',
        'type': lambda *args: 'directory',
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
            path.append(self.pool.get(directory.ressource_type_id.model).browse(cr,uid,res_id).name)
            user=self.pool.get('res.users').browse(cr,uid,uid)
            #print "ftp://%s:%s@localhost:8021/%s/%s"%(user.login,user.password,cr.dbname,'/'.join(path))
            return "ftp://%s:%s@localhost:8021/%s/%s"%(user.login,user.password,cr.dbname,'/'.join(path))
        return False
    def _check_duplication(self, cr, uid,vals):
        if 'name' in vals:
            where=" name='%s'"% (vals['name'])
            if not 'parent_id' in vals or not vals['parent_id']:
                where+=' and parent_id is null'
            else:
                where+=' and parent_id=%d'%(vals['parent_id'])
            if not 'ressource_parent_type_id' in vals or not vals['ressource_parent_type_id']:
                where+= ' and ressource_parent_type_id is null'
            else:
                where+=" and ressource_parent_type_id='%s'"%(vals['ressource_parent_type_id'])
#            if not 'ressource_id' in vals or not vals['ressource_id']:
#                where+= ' and ressource_id is null'
#            else:
#                where+=" and ressource_id=%d"%(vals['ressource_id'])
            cr.execute("select id from document_directory where" + where)
            res = cr.fetchall()
            if len(res):
                return False
        return True
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
        self._cache = {}
        return res

    def onchange_content_id(self, cr, uid, ids, ressource_type_id):
        return {}

    def _get_childs(self, cr, uid, node, nodename=False, context={}):
        where = []
        if nodename:
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
    def get_object(self, cr, uid, uri, context={}):
        if not uri:
            return node_class(cr, uid, '', False, type='database')
        turi = tuple(uri)
        if False and (turi in self._cache):
            (path, oo, oo2, content,type,root) = self._cache[turi]
            if oo:
                object = self.pool.get(oo[0]).browse(cr, uid, oo[1], context)
            else:
                object = False
            if oo2:
                object2 = self.pool.get(oo2[0]).browse(cr, uid, oo2[1], context)
            else:
                object2 = False
            node = node_class(cr, uid, path, object,object2, context, content, type, root)
            return node

        node = node_class(cr, uid, '/', False, type='database')
        for path in uri[:]:
            if path:
                node = node.child(path)
                if not node:
                    return False
        oo = node.object and (node.object._name, node.object.id) or False
        oo2 = node.object2 and (node.object2._name, node.object2.id) or False
        self._cache[turi] = (node.path, oo, oo2, node.content,node.type,node.root)
        return node

    def get_childs(self, cr, uid, uri, context={}):
        node = self.get_object(cr, uid, uri, context)
        if uri:
            children = node.children()
        else:
            children= [node]
        result = map(lambda node: node.path_get(), children)
        #childs,object2 = self._get_childs(cr, uid, object, False, context)
        #result = map(lambda x: urlparse.urljoin(path+'/',x.name), childs)
        return result

    def write(self, cr, uid, ids, vals, context=None):
        # need to make constraints to checking duplicate
        #if not self._check_duplication(cr,uid,vals):
        #    raise except_orm('ValidateError', 'Directory name must be unique!')
        return super(document_directory,self).write(cr,uid,ids,vals,context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default ={}
        name = self.read(cr, uid, [id])[0]['name']
        default.update({'name': name+ " (copy)"})
        return super(document_directory,self).copy(cr,uid,id,default,context)

    def create(self, cr, uid, vals, context=None):
        if not self._check_duplication(cr,uid,vals):
            raise except_orm('ValidateError', 'Directory name must be unique!')
        if vals.get('name',False) and (vals.get('name').find('/')+1 or vals.get('name').find('@')+1 or vals.get('name').find('$')+1 or vals.get('name').find('#')+1) :
            raise 'Error'
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
    def _extension_get(self, cr, uid, context={}):
        cr.execute('select code,name from document_directory_content_type where active')
        res = cr.fetchall()
        return res
    _columns = {
        'name': fields.char('Content Name', size=64, required=True),
        'sequence': fields.integer('Sequence', size=16),
        'suffix': fields.char('Suffix', size=16),
        'report_id': fields.many2one('ir.actions.report.xml', 'Report'),
        'extension': fields.selection(_extension_get, 'Report Type', required=True, size=4),
        'include_name': fields.boolean('Include Record Name', help="Check if you cant that the name of the file start by the record name."),
        'directory_id': fields.many2one('document.directory', 'Directory'),
    }
    _defaults = {
        'extension': lambda *args: '.pdf',
        'sequence': lambda *args: 1,
        'include_name': lambda *args: 1,
    }
    def process_read_pdf(self, cr, uid, node, context={}):
        report = self.pool.get('ir.actions.report.xml').browse(cr, uid, node.report_id.id)
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

    def _model_search(self, cr, uid, obj, name, args):
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


import random
import string


def random_name():
    random.seed()
    d = [random.choice(string.letters) for x in xrange(10) ]
    name = "".join(d)
    return name


def create_directory(path):
    dir_name = random_name()
    path = os.path.join(path,dir_name)
    os.mkdir(path)
    return dir_name

class document_file(osv.osv):
    _inherit = 'ir.attachment'
    def _data_get(self, cr, uid, ids, name, arg, context):
        result = {}
        cr.execute('select id,store_method,datas,store_fname,link from ir_attachment where id in ('+','.join(map(str,ids))+')')
        for id,m,d,r,l in cr.fetchall():
            if m=='db':
                result[id] = d
            elif m=='fs':
                try:
                    path = os.path.join(os.getcwd(),'filestore')
                    value = file(os.path.join(path,r), 'rb').read()
                    result[id] = base64.encodestring(value)
                except:
                    result[id]=''
            else:
                result[id] = ''
        return result

    #
    # This code can be improved
    #
    def _data_set(self, cr, obj, id, name, value, uid=None, context={}):
        if not value:
            return True
        if (not context) or context.get('store_method','fs')=='fs':
            path = os.path.join(os.getcwd(), "filestore")
            if not os.path.isdir(path):
                os.mkdir(path)
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
            cr.execute('update ir_attachment set store_fname=%s,store_method=%s,file_size=%d where id=%d', (os.path.join(flag,filename),'fs',len(v),id))
        else:
            cr.execute('update ir_attachment set datas=%s,store_method=%s where id=%d', (psycopg.Binary(value),'db',id))
        return True

    _columns = {
        'user_id': fields.many2one('res.users', 'Owner', select=1),
        'group_ids': fields.many2many('res.groups', 'document_directory_group_rel', 'item_id', 'group_id', 'Groups'),
        'parent_id': fields.many2one('document.directory', 'Directory', select=1),
        'file_size': fields.integer('File Size', required=True),
        'file_type': fields.char('Content Type', size=32),
        'index_content': fields.text('Indexed Content'),
        'write_date': fields.datetime('Date Modified', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True),
        'create_date': fields.datetime('Date Created', readonly=True),
        'create_uid':  fields.many2one('res.users', 'Creator', readonly=True),
        'store_method': fields.selection([('db','Database'),('fs','Filesystem'),('link','Link')], "Storing Method"),
        'datas': fields.function(_data_get,method=True,store=True,fnct_inv=_data_set,string='File Content',type="binary"),
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

    def _check_duplication(self, cr, uid,vals):
        if 'name' in vals:
            res=self.search(cr,uid,[('name','=',vals['name']),('parent_id','=','parent_id' in vals and vals['parent_id'] or False),('res_id','=','res_id' in vals and vals['res_id'] or False),('res_model','=','res_model' in vals and vals['res_model']) or False])
            if len(res):
                return False
        return True

    def write(self, cr, uid, ids, vals, context=None):
        if not self._check_duplication(cr,uid,vals):
            raise except_orm('ValidateError', 'File name must be unique!')
        result = super(document_file,self).write(cr,uid,ids,vals,context=context)
        try:
            for f in self.browse(cr, uid, ids, context=context):
                if 'datas' not in vals:
                    vals['datas']=f.datas
                res = content_index(base64.decodestring(vals['datas']), f.datas_fname, f.file_type or None)
                super(document_file,self).write(cr, uid, ids, {
                    'index_content': res
                })
        except:
            pass
        return result

    def create(self, cr, uid, vals, context={}):
        vals['title']=vals['name']
        if vals.get('res_id', False) and vals.get('res_model',False):
            obj_model=self.pool.get(vals['res_model'])
            result = obj_model.read(cr, uid, [vals['res_id']], context=context)
            if len(result):
                obj=result[0]
                vals['title'] = (obj['name'] or '')[:60]
                if obj_model._name=='res.partner':
                    vals['partner_id']=obj['id']
                elif 'address_id' in obj:
                    address=self.pool.get('res.partner.address').read(cr,uid,[obj['address_id']],context=context)
                    if len(address):
                        vals['partner_id']=address[0]['partner_id'] or False
                elif 'partner_id' in obj:
                    if isinstance(obj['partner_id'],tuple) or isinstance(obj['partner_id'],list):
                        vals['partner_id']=obj['partner_id'][0]
                    else:
                        vals['partner_id']=obj['partner_id']

        datas=None
        if 'datas' not in vals:
            import urllib
            datas=base64.encodestring(urllib.urlopen(vals['link']).read())
        else:
            datas=vals['datas']
        vals['file_size']= len(datas)
        if not self._check_duplication(cr,uid,vals):
            raise except_orm('ValidateError', 'File name must be unique!')
        result = super(document_file,self).create(cr, uid, vals, context)
        cr.commit()
        try:
            res = content_index(base64.decodestring(datas), vals['datas_fname'], vals.get('content_type', None))
            super(document_file,self).write(cr, uid, [result], {
                'index_content': res,
            })
            cr.commit()
        except:
            pass
        return result

    def unlink(self,cr, uid, ids, context={}):
        for f in self.browse(cr, uid, ids, context):
            if f.store_method=='fs':
                try:
                    path = os.path.join(os.getcwd(),'filestore',f.store_fname)
                    os.unlink(path)
                except:
                    pass
        return super(document_file, self).unlink(cr, uid, ids, context)
document_file()

class document_configuration_wizard(osv.osv_memory):
    _name='document.configuration.wizard'
    _rec_name = 'Auto Directory configuration'
    _columns = {
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
        obj=self.pool.get('document.directory')
        search_ids=obj.search(cr,uid,[])
        browse_lst=obj.browse(cr,uid,search_ids)
        model_obj=self.pool.get('ir.model')

        for doc_obj in browse_lst:            
            if doc_obj.name in ('Partner','Contacts','Personnal Folders','Partner Category','Sales Order','All Sales Order','Sales by Salesman','Projects'):
                res={}
                id=[]
                if doc_obj.name=='Partner':
                    id=model_obj.search(cr,uid,[('model','=','res.partner')])

                if doc_obj.name=='Contacts':
                    id=model_obj.search(cr,uid,[('model','=','res.partner.address')])

                if doc_obj.name=='Partner Category':
                    id=model_obj.search(cr,uid,[('model','=','res.partner.category')])

                if  doc_obj.name=='All Sales Order':
                    val={}
                    id=model_obj.search(cr,uid,[('model','=','sale.order')])
                    print 'Found', id
                    if id and not len(doc_obj.content_ids):
                        val['name']='Sale Report'
                        val['suffix']='_report'
                        val['report_id']=self.pool.get('ir.actions.report.xml').search(cr,uid,[('report_name','=','sale.order')])[0]
                        val['extension']='.pdf'
                        val['directory_id']=doc_obj.id
                        self.pool.get('document.directory.content').create(cr,uid,val)

                if doc_obj.name=='Sales by Salesman':
                    id=model_obj.search(cr,uid,[('model','=','res.users')])

                if doc_obj.name=='Personnal Folders':
                    id=model_obj.search(cr,uid,[('model','=','res.users')])

                if doc_obj.name=='Projects':
                    id=model_obj.search(cr,uid,[('model','=','account.analytic.account')])
                    res['ressource_tree']=True

                if id:
                    res['ressource_type_id']=id[0]
                    res['type']='ressource'
                    obj.write(cr,uid,doc_obj.id,res)
        self.create_folder(cr, uid, ids, context=None)
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
            }

    def create_folder(self, cr, uid, ids, context=None):
        doc_obj=self.pool.get('document.directory')
        model_obj=self.pool.get('ir.model')
        for name in ('Sales','Quotation','Meetings','Analysis Reports'):
            res={}
            if name=='Sales':
                child_model=model_obj.search(cr,uid,[('model','=','sale.order')])
                link_model=model_obj.search(cr,uid,[('model','=','res.users')])
                if child_model:
                    res['type']='ressource'
                    res['ressource_type_id']=child_model[0]
                    res['ressource_parent_type_id']=link_model[0]
                    res['domain']="[('user_id','=',active_id)]"
            else:
                link_model=model_obj.search(cr,uid,[('model','=','account.analytic.account')])
                if link_model:
                    res['ressource_parent_type_id']=link_model[0]
                    res['ressource_id']=0
            if res:
                res['name']=name
                doc_obj.create(cr,uid,res)
        return True

document_configuration_wizard()
