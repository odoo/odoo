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
import errno
import logging
import os
import random
import shutil
import string
import time
from StringIO import StringIO

import psycopg2

import openerp
from openerp import netsvc
from openerp import pooler
from openerp import tools
from openerp.osv import fields, osv
from openerp.osv.orm import except_orm
from openerp.tools.misc import ustr
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval

from content_index import cntIndex

_logger = logging.getLogger(__name__)

class document_file(osv.osv):
    _inherit = 'ir.attachment'

    _columns = {
        # Columns from ir.attachment:
        'write_date': fields.datetime('Date Modified', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True),
        # Fields of document:
        'user_id': fields.many2one('res.users', 'Owner', select=1),
        'parent_id': fields.many2one('document.directory', 'Directory', select=1, change_default=True),
        'index_content': fields.text('Indexed Content'),
        'partner_id':fields.many2one('res.partner', 'Partner', select=1),
        'file_type': fields.char('Content Type'),
    }
    _order = "id desc"

    _defaults = {
        'user_id': lambda self, cr, uid, ctx:uid,
    }

    _sql_constraints = [
        ('filename_unique', 'unique (name,parent_id)', 'The filename must be unique in a directory !'),
    ]

    def check(self, cr, uid, ids, mode, context=None, values=None):
        """Check access wrt. res_model, relax the rule of ir.attachment parent
        With 'document' installed, everybody will have access to attachments of
        any resources they can *read*.
        """
        return super(document_file, self).check(cr, uid, ids, mode='read', context=context, values=values)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # Grab ids, bypassing 'count'
        ids = super(document_file, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=False)
        if not ids:
            return 0 if count else []

        # Filter out documents that are in directories that the user is not allowed to read.
        # Must use pure SQL to avoid access rules exceptions (we want to remove the records,
        # not fail), and the records have been filtered in parent's search() anyway.
        cr.execute('SELECT id, parent_id from ir_attachment WHERE id in %s', (tuple(ids),))

        # cont a dict of parent -> attach
        parents = {}
        for attach_id, attach_parent in cr.fetchall():
            parents.setdefault(attach_parent, []).append(attach_id)
        parent_ids = parents.keys()

        # filter parents
        visible_parent_ids = self.pool.get('document.directory').search(cr, uid, [('id', 'in', list(parent_ids))])

        # null parents means allowed
        ids = parents.get(None,[])
        for parent_id in visible_parent_ids:
            ids.extend(parents[parent_id])

        return len(ids) if count else ids

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        if 'name' not in default:
            name = self.read(cr, uid, [id], ['name'])[0]['name']
            default.update(name=_("%s (copy)") % (name))
        return super(document_file, self).copy(cr, uid, id, default, context=context)

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        vals['parent_id'] = context.get('parent_id', False) or vals.get('parent_id', False)
        # take partner from uid
        if vals.get('res_id', False) and vals.get('res_model', False) and not vals.get('partner_id', False):
            vals['partner_id'] = self.__get_partner_id(cr, uid, vals['res_model'], vals['res_id'], context)
        if vals.get('datas', False):
            vals['file_type'], vals['index_content'] = self._index(cr, uid, vals['datas'].decode('base64'), vals.get('datas_fname', False), None)
        return super(document_file, self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if vals.get('datas', False):
            vals['file_type'], vals['index_content'] = self._index(cr, uid, vals['datas'].decode('base64'), vals.get('datas_fname', False), None)
        return super(document_file, self).write(cr, uid, ids, vals, context)

    def _index(self, cr, uid, data, datas_fname, file_type):
        mime, icont = cntIndex.doIndex(data, datas_fname,  file_type or None, None)
        icont_u = ustr(icont)
        return mime, icont_u

    def __get_partner_id(self, cr, uid, res_model, res_id, context=None):
        """ A helper to retrieve the associated partner from any res_model+id
            It is a hack that will try to discover if the mentioned record is
            clearly associated with a partner record.
        """
        obj_model = self.pool.get(res_model)
        if obj_model._name == 'res.partner':
            return res_id
        elif 'partner_id' in obj_model._columns and obj_model._columns['partner_id']._obj == 'res.partner':
            bro = obj_model.browse(cr, uid, res_id, context=context)
            return bro.partner_id.id
        return False

class document_directory(osv.osv):
    _name = 'document.directory'
    _description = 'Directory'
    _order = 'name'
    _columns = {
        'name': fields.char('Name', size=64, required=True, select=1),
        'write_date': fields.datetime('Date Modified', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True),
        'create_date': fields.datetime('Date Created', readonly=True),
        'create_uid':  fields.many2one('res.users', 'Creator', readonly=True),
        'user_id': fields.many2one('res.users', 'Owner'),
        'group_ids': fields.many2many('res.groups', 'document_directory_group_rel', 'item_id', 'group_id', 'Groups'),
        'parent_id': fields.many2one('document.directory', 'Parent Directory', select=1, change_default=True),
        'child_ids': fields.one2many('document.directory', 'parent_id', 'Children'),
        'file_ids': fields.one2many('ir.attachment', 'parent_id', 'Files'),
        'content_ids': fields.one2many('document.directory.content', 'directory_id', 'Virtual Files'),
        'type': fields.selection([ ('directory','Static Directory'), ('ressource','Folders per resource'), ],
            'Type', required=True, select=1, change_default=True,
            help="Each directory can either have the type Static or be linked to another resource. A static directory, as with Operating Systems, is the classic directory that can contain a set of files. The directories linked to systems resources automatically possess sub-directories for each of resource types defined in the parent directory."),
        'domain': fields.char('Domain', size=128, help="Use a domain if you want to apply an automatic filter on visible resources."),
        'ressource_type_id': fields.many2one('ir.model', 'Resource model', change_default=True,
            help="Select an object here and there will be one folder per record of that resource."),
        'resource_field': fields.many2one('ir.model.fields', 'Name field', help='Field to be used as name on resource directories. If empty, the "name" will be used.'),
        'resource_find_all': fields.boolean('Find all resources',
                help="If true, all attachments that match this resource will " \
                    " be located. If false, only ones that have this as parent." ),
        'ressource_parent_type_id': fields.many2one('ir.model', 'Parent Model', change_default=True,
            help="If you put an object here, this directory template will appear bellow all of these objects. " \
                 "Such directories are \"attached\" to the specific model or record, just like attachments. " \
                 "Don't put a parent directory if you select a parent model."),
        'ressource_id': fields.integer('Resource ID',
            help="Along with Parent Model, this ID attaches this folder to a specific record of Parent Model."),
        'ressource_tree': fields.boolean('Tree Structure',
            help="Check this if you want to use the same tree structure as the object selected in the system."),
        'dctx_ids': fields.one2many('document.directory.dctx', 'dir_id', 'Context fields'),
        'company_id': fields.many2one('res.company', 'Company', change_default=True),
    }

    _defaults = {
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'document.directory', context=c),
        'user_id': lambda self,cr,uid,ctx: uid,
        'domain': '[]',
        'type': 'directory',
        'ressource_id': 0,
        'resource_find_all': True,
    }
    _sql_constraints = [
        ('dirname_uniq', 'unique (name,parent_id,ressource_id,ressource_parent_type_id)', 'The directory name must be unique !'),
        ('no_selfparent', 'check(parent_id <> id)', 'Directory cannot be parent of itself!'),
    ]
    def name_get(self, cr, uid, ids, context=None):
        res = []
        if not self.search(cr,uid,[('id','in',ids)]):
            ids = []
        for d in self.browse(cr, uid, ids, context=context):
            s = ''
            d2 = d
            while d2 and d2.parent_id:
                s = d2.name + (s and ('/' + s) or '')
                d2 = d2.parent_id
            res.append((d.id, s or d.name))
        return res

    def get_full_path(self, cr, uid, dir_id, context=None):
        """ Return the full path to this directory, in a list, root first
        """
        if isinstance(dir_id, (tuple, list)):
            assert len(dir_id) == 1
            dir_id = dir_id[0]

        def _parent(dir_id, path):
            parent=self.browse(cr, uid, dir_id)
            if parent.parent_id and not parent.ressource_parent_type_id:
                _parent(parent.parent_id.id,path)
                path.append(parent.name)
            else:
                path.append(parent.name)
                return path
        path = []
        _parent(dir_id, path)
        return path

    def _check_recursion(self, cr, uid, ids, context=None):
        level = 100
        while len(ids):
            cr.execute('select distinct parent_id from document_directory where id in ('+','.join(map(str,ids))+')')
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, 'Error! You cannot create recursive directories.', ['parent_id'])
    ]

    def onchange_content_id(self, cr, uid, ids, ressource_type_id):
        return {}

    def get_object(self, cr, uid, uri, context=None):
        """ Return a node object for the given uri.
           This fn merely passes the call to node_context
        """
        return get_node_context(cr, uid, context).get_uri(cr, uri)

    def get_node_class(self, cr, uid, ids, dbro=None, dynamic=False, context=None):
        """Retrieve the class of nodes for this directory

           This function can be overriden by inherited classes ;)
           @param dbro The browse object, if caller already has it
        """
        if dbro is None:
            dbro = self.browse(cr, uid, ids, context=context)

        if dynamic:
            return node_res_obj
        elif dbro.type == 'directory':
            return node_dir
        elif dbro.type == 'ressource':
            return node_res_dir
        else:
            raise ValueError("dir node for %s type.", dbro.type)

    def _prepare_context(self, cr, uid, nctx, context=None):
        """ Fill nctx with properties for this database
        @param nctx instance of nodes.node_context, to be filled
        @param context ORM context (dict) for us

        Note that this function is called *without* a list of ids,
        it should behave the same for the whole database (based on the
        ORM instance of document.directory).

        Some databases may override this and attach properties to the
        node_context. See WebDAV, CalDAV.
        """
        return

    def get_dir_permissions(self, cr, uid, ids, context=None):
        """Check what permission user 'uid' has on directory 'id'
        """
        assert len(ids) == 1

        res = 0
        for pperms in [('read', 5), ('write', 2), ('unlink', 8)]:
            try:
                self.check_access_rule(cr, uid, ids, pperms[0], context=context)
                res |= pperms[1]
            except except_orm:
                pass
        return res

    def _locate_child(self, cr, uid, root_id, uri, nparent, ncontext):
        """ try to locate the node in uri,
            Return a tuple (node_dir, remaining_path)
        """
        return (node_database(context=ncontext), uri)

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default ={}
        name = self.read(cr, uid, [id])[0]['name']
        default.update(name=_("%s (copy)") % (name))
        return super(document_directory,self).copy(cr, uid, id, default, context=context)

    def _check_duplication(self, cr, uid, vals, ids=None, op='create'):
        name=vals.get('name',False)
        parent_id=vals.get('parent_id',False)
        ressource_parent_type_id=vals.get('ressource_parent_type_id',False)
        ressource_id=vals.get('ressource_id',0)
        if op=='write':
            for directory in self.browse(cr, uid, ids):
                if not name:
                    name=directory.name
                if not parent_id:
                    parent_id=directory.parent_id and directory.parent_id.id or False
                # TODO fix algo
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
        if not self._check_duplication(cr, uid, vals, ids, op='write'):
            raise osv.except_osv(_('ValidateError'), _('Directory name must be unique!'))
        return super(document_directory,self).write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, vals, context=None):
        if not self._check_duplication(cr, uid, vals):
            raise osv.except_osv(_('ValidateError'), _('Directory name must be unique!'))
        newname = vals.get('name',False)
        if newname:
            for illeg in ('/', '@', '$', '#'):
                if illeg in newname:
                    raise osv.except_osv(_('ValidateError'), _('Directory name contains special characters!'))
        return super(document_directory,self).create(cr, uid, vals, context)

class document_directory_dctx(osv.osv):
    """ In order to evaluate dynamic folders, child items could have a limiting
        domain expression. For that, their parents will export a context where useful
        information will be passed on.
        If you define sth like "s_id" = "this.id" at a folder iterating over sales, its
        children could have a domain like [('sale_id', = ,s_id )]
        This system should be used recursively, that is, parent dynamic context will be
        appended to all children down the tree.
    """
    _name = 'document.directory.dctx'
    _description = 'Directory Dynamic Context'
    _columns = {
        'dir_id': fields.many2one('document.directory', 'Directory', required=True, ondelete="cascade"),
        'field': fields.char('Field', size=20, required=True, select=1, help="The name of the field."),
        'expr': fields.char('Expression', size=64, required=True, help="A python expression used to evaluate the field.\n" + \
                "You can use 'dir_id' for current dir, 'res_id', 'res_model' as a reference to the current record, in dynamic folders"),
        }

class document_directory_content_type(osv.osv):
    _name = 'document.directory.content.type'
    _description = 'Directory Content Type'
    _columns = {
        'name': fields.char('Content Type', size=64, required=True),
        'code': fields.char('Extension', size=4),
        'active': fields.boolean('Active'),
        'mimetype': fields.char('Mime Type',size=32)
    }
    _defaults = {
        'active': lambda *args: 1
    }

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
        'prefix': fields.char('Prefix', size=16),
        'suffix': fields.char('Suffix', size=16),
        'report_id': fields.many2one('ir.actions.report.xml', 'Report'),
        'extension': fields.selection(_extension_get, 'Document Type', required=True, size=4),
        'include_name': fields.boolean('Include Record Name', 
                help="Check this field if you want that the name of the file to contain the record name." \
                    "\nIf set, the directory will have to be a resource one."),
        'directory_id': fields.many2one('document.directory', 'Directory'),
    }
    _defaults = {
        'extension': lambda *args: '.pdf',
        'sequence': lambda *args: 1,
        'include_name': lambda *args: 1,
    }
    
    def _file_get(self, cr, node, nodename, content, context=None):
        """ return the nodes of a <node> parent having a <content> content
            The return value MUST be false or a list of node_class objects.
        """
    
        # TODO: respect the context!
        model = node.res_model
        if content.include_name and not model:
            return False
        
        res2 = []
        tname = ''
        if content.include_name:
            record_name = node.displayname or ''
            # obj = node.context._dirobj.pool.get(model)
            if record_name:
                tname = (content.prefix or '') + record_name + (content.suffix or '') + (content.extension or '')
        else:
            tname = (content.prefix or '') + (content.name or '') + (content.suffix or '') + (content.extension or '')
        if tname.find('/'):
            tname=tname.replace('/', '_')
        act_id = False
        if 'dctx_res_id' in node.dctx:
            act_id = node.dctx['res_id']
        elif hasattr(node, 'res_id'):
            act_id = node.res_id
        else:
            act_id = node.context.context.get('res_id',False)
        if not nodename:
            n = node_content(tname, node, node.context,content, act_id=act_id)
            res2.append( n)
        else:
            if nodename == tname:
                n = node_content(tname, node, node.context,content, act_id=act_id)
                n.fill_fields(cr)
                res2.append(n)
        return res2

    def process_write(self, cr, uid, node, data, context=None):
        if node.extension != '.pdf':
            raise Exception("Invalid content: %s" % node.extension)
        return True
    
    def process_read(self, cr, uid, node, context=None):
        if node.extension != '.pdf':
            raise Exception("Invalid content: %s" % node.extension)
        report = self.pool.get('ir.actions.report.xml').browse(cr, uid, node.report_id, context=context)
        srv = netsvc.Service._services['report.'+report.report_name]
        ctx = node.context.context.copy()
        ctx.update(node.dctx)
        pdf,pdftype = srv.create(cr, uid, [node.act_id,], {}, context=ctx)
        return pdf

class ir_action_report_xml(osv.osv):
    _name="ir.actions.report.xml"
    _inherit ="ir.actions.report.xml"

    def _model_get(self, cr, uid, ids, name, arg, context=None):
        res = {}
        model_pool = self.pool.get('ir.model')
        for data in self.read(cr, uid, ids, ['model']):
            model = data.get('model',False)
            if model:
                model_id =model_pool.search(cr, uid, [('model','=',model)])
                if model_id:
                    res[data.get('id')] = model_id[0]
                else:
                    res[data.get('id')] = False
        return res

    def _model_search(self, cr, uid, obj, name, args, context=None):
        if not len(args):
            return []
        assert len(args) == 1 and args[0][1] == '=', 'expression is not what we expect: %r' % args
        model_id= args[0][2]
        if not model_id:
            # a deviation from standard behavior: when searching model_id = False
            # we return *all* reports, not just ones with empty model.
            # One reason is that 'model' is a required field so far
            return []
        model = self.pool.get('ir.model').read(cr, uid, [model_id])[0]['model']
        report_id = self.search(cr, uid, [('model','=',model)])
        if not report_id:
            return [('id','=','0')]
        return [('id','in',report_id)]

    _columns={
        'model_id' : fields.function(_model_get, fnct_search=_model_search, string='Model Id'),
    }

class document_storage(osv.osv):
    """ The primary object for data storage. Deprecated.  """
    _name = 'document.storage'
    _description = 'Storage Media'

    def get_data(self, cr, uid, id, file_node, context=None, fil_obj=None):
        """ retrieve the contents of some file_node having storage_id = id
            optionally, fil_obj could point to the browse object of the file
            (ir.attachment)
        """
        boo = self.browse(cr, uid, id, context=context)
        if fil_obj:
            ira = fil_obj
        else:
            ira = self.pool.get('ir.attachment').browse(cr, uid, file_node.file_id, context=context)
        data = ira.datas
        if data:
            out = data.decode('base64')
        else:
            out = ''
        return out

    def get_file(self, cr, uid, id, file_node, mode, context=None):
        """ Return a file-like object for the contents of some node
        """
        if context is None:
            context = {}
        boo = self.browse(cr, uid, id, context=context)

        ira = self.pool.get('ir.attachment').browse(cr, uid, file_node.file_id, context=context)
        return nodefd_db(file_node, ira_browse=ira, mode=mode)

    def set_data(self, cr, uid, id, file_node, data, context=None, fil_obj=None):
        """ store the data.
            This function MUST be used from an ir.attachment. It wouldn't make sense
            to store things persistently for other types (dynamic).
        """
        boo = self.browse(cr, uid, id, context=context)
        if fil_obj:
            ira = fil_obj
        else:
            ira = self.pool.get('ir.attachment').browse(cr, uid, file_node.file_id, context=context)

        _logger.debug( "Store data for ir.attachment #%d." % ira.id)
        store_fname = None
        fname = None
        filesize = len(data)
        self.pool.get('ir.attachment').write(cr, uid, [file_node.file_id], {'datas': data.encode('base64')}, context=context)
        # 2nd phase: store the metadata
        try:
            icont = ''
            mime = ira.file_type
            if not mime:
                mime = ""
            try:
                mime, icont = cntIndex.doIndex(data, ira.datas_fname, ira.file_type or None, fname)
            except Exception:
                _logger.debug('Cannot index file.', exc_info=True)
                pass
            try:
                icont_u = ustr(icont)
            except UnicodeError:
                icont_u = ''
            # a hack: /assume/ that the calling write operation will not try
            # to write the fname and size, and update them in the db concurrently.
            # We cannot use a write() here, because we are already in one.
            cr.execute('UPDATE ir_attachment SET file_size = %s, index_content = %s, file_type = %s WHERE id = %s', (filesize, icont_u, mime, file_node.file_id))
            file_node.content_length = filesize
            file_node.content_type = mime
            return True
        except Exception, e :
            _logger.warning("Cannot save data.", exc_info=True)
            # should we really rollback once we have written the actual data?
            # at the db case (only), that rollback would be safe
            raise except_orm(_('Error at doc write!'), str(e))

def _str2time(cre):
    """ Convert a string with time representation (from db) into time (float)

        Note: a place to fix if datetime is used in db.
    """
    if not cre:
        return time.time()
    frac = 0.0
    if isinstance(cre, basestring) and '.' in cre:
        fdot = cre.find('.')
        frac = float(cre[fdot:])
        cre = cre[:fdot]
    return time.mktime(time.strptime(cre,'%Y-%m-%d %H:%M:%S')) + frac

def get_node_context(cr, uid, context):
    return node_context(cr, uid, context)

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

class node_context(object):
    """ This is the root node, representing access to some particular context

    A context is a set of persistent data, which may influence the structure
    of the nodes. All other transient information during a data query should
    be passed down with function arguments.
    """
    cached_roots = {}
    node_file_class = None

    def __init__(self, cr, uid, context=None):
        self.dbname = cr.dbname
        self.uid = uid
        self.context = context
        if context is None:
            context = {}
        context['uid'] = uid
        self._dirobj = pooler.get_pool(cr.dbname).get('document.directory')
        self.node_file_class = node_file
        self.extra_ctx = {} # Extra keys for context, that do _not_ trigger inequality
        assert self._dirobj
        self._dirobj._prepare_context(cr, uid, self, context=context)
        self.rootdir = False #self._dirobj._get_root_directory(cr,uid,context)

    def __eq__(self, other):
        if not type(other) == node_context:
            return False
        if self.dbname != other.dbname:
            return False
        if self.uid != other.uid:
            return False
        if self.context != other.context:
            return False
        if self.rootdir != other.rootdir:
            return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def get(self, name, default=None):
        return self.context.get(name, default)

    def get_uri(self, cr, uri):
        """ Although this fn passes back to doc.dir, it is needed since
            it is a potential caching point.
        """
        (ndir, duri) =  self._dirobj._locate_child(cr, self.uid, self.rootdir, uri, None, self)
        while duri:
            ndir = ndir.child(cr, duri[0])
            if not ndir:
                return False
            duri = duri[1:]
        return ndir

    def get_dir_node(self, cr, dbro):
        """Create (or locate) a node for a directory
            @param dbro a browse object of document.directory
        """

        fullpath = dbro.get_full_path(context=self.context)
        klass = dbro.get_node_class(dbro, context=self.context)
        return klass(fullpath, None ,self, dbro)

    def get_file_node(self, cr, fbro):
        """ Create or locate a node for a static file
            @param fbro a browse object of an ir.attachment
        """
        parent = None
        if fbro.parent_id:
            parent = self.get_dir_node(cr, fbro.parent_id)

        return self.node_file_class(fbro.name, parent, self, fbro)

class node_class(object):
    """ this is a superclass for our inodes
        It is an API for all code that wants to access the document files.
        Nodes have attributes which contain usual file properties
        """
    our_type = 'baseclass'
    DAV_PROPS = None
    DAV_M_NS = None

    def __init__(self, path, parent, context):
        assert isinstance(context,node_context)
        assert (not parent ) or isinstance(parent,node_class)
        self.path = path
        self.context = context
        self.type=self.our_type
        self.parent = parent
        self.uidperms = 5   # computed permissions for our uid, in unix bits
        self.mimetype = 'application/octet-stream'
        self.create_date = None
        self.write_date = None
        self.unixperms = 0660
        self.uuser = 'user'
        self.ugroup = 'group'
        self.content_length = 0
        # dynamic context:
        self.dctx = {}
        if parent:
            self.dctx = parent.dctx.copy()
        self.displayname = 'Object'

    def __eq__(self, other):
        return NotImplemented

    def __ne__(self, other):
        return not self.__eq__(other)

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
        elif self.path is None:
            s.append('')
        else:
            s.append(self.path)
        return s #map(lambda x: '/' +x, s)

    def __repr__(self):
        return "%s@/%s" % (self.our_type, '/'.join(self.full_path()))

    def children(self, cr, domain=None):
        print "node_class.children()"
        return [] #stub

    def child(self, cr, name, domain=None):
        print "node_class.child()"
        return None

    def get_uri(self, cr, uri):
        duri = uri
        ndir = self
        while duri:
            ndir = ndir.child(cr, duri[0])
            if not ndir:
                return False
            duri = duri[1:]
        return ndir

    def path_get(self):
        print "node_class.path_get()"
        return False

    def get_data(self, cr):
        raise TypeError('No data for %s.'% self.type)

    def open_data(self, cr, mode):
        """ Open a node_descriptor object for this node.

        @param the mode of open, eg 'r', 'w', 'a', like file.open()

        This operation may lock the data for this node (and accross
        other node hierarchies), until the descriptor is close()d. If
        the node is locked, subsequent opens (depending on mode) may
        immediately fail with an exception (which?).
        For this class, there is no data, so no implementation. Each
        child class that has data should override this.
        """
        raise TypeError('No data for %s.' % self.type)

    def get_etag(self, cr):
        """ Get a tag, unique per object + modification.

            see. http://tools.ietf.org/html/rfc2616#section-13.3.3 """
        return '"%s-%s"' % (self._get_ttag(cr), self._get_wtag(cr))

    def _get_wtag(self, cr):
        """ Return the modification time as a unique, compact string """
        return str(_str2time(self.write_date)).replace('.','')

    def _get_ttag(self, cr):
        """ Get a unique tag for this type/id of object.
            Must be overriden, so that each node is uniquely identified.
        """
        print "node_class.get_ttag()",self
        raise NotImplementedError("get_ttag stub()")

    def get_dav_props(self, cr):
        """ If this class has special behaviour for GroupDAV etc, export
        its capabilities """
        # This fn is placed here rather than WebDAV, because we want the
        # baseclass methods to apply to all node subclasses
        return self.DAV_PROPS or {}

    def match_dav_eprop(self, cr, match, ns, prop):
        res = self.get_dav_eprop(cr, ns, prop)
        if res == match:
            return True
        return False

    def get_dav_eprop(self, cr, ns, prop):
        if not self.DAV_M_NS:
            return None

        if self.DAV_M_NS.has_key(ns):
            prefix = self.DAV_M_NS[ns]
        else:
            _logger.debug('No namespace: %s ("%s").',ns, prop)
            return None

        mname = prefix + "_" + prop.replace('-','_')

        if not hasattr(self, mname):
            return None

        try:
            m = getattr(self, mname)
            r = m(cr)
            return r
        except AttributeError:
            _logger.debug('The property %s is not supported.' % prop, exc_info=True)
        return None

    def get_dav_resourcetype(self, cr):
        """ Get the DAV resource type.

            Is here because some nodes may exhibit special behaviour, like
            CalDAV/GroupDAV collections
        """
        raise NotImplementedError

    def move_to(self, cr, ndir_node, new_name=False, fil_obj=None, ndir_obj=None, in_write=False):
        """ Move this node to a new parent directory.
        @param ndir_node the collection that this node should be moved under
        @param new_name a name to rename this node to. If omitted, the old
            name is preserved
        @param fil_obj, can be None, is the browse object for the file,
            if already available.
        @param ndir_obj must be the browse object to the new doc.directory
            location, where this node should be moved to.
        in_write: When called by write(), we shouldn't attempt to write the
            object, but instead return the dict of vals (avoid re-entrance).
            If false, we should write all data to the object, here, as if the
            caller won't do anything after calling move_to()

        Return value:
            True: the node is moved, the caller can update other values, too.
            False: the node is either removed or fully updated, the caller
                must discard the fil_obj, not attempt to write any more to it.
            dict: values to write back to the object. *May* contain a new id!

        Depending on src and target storage, implementations of this function
        could do various things.
        Should also consider node<->content, dir<->dir moves etc.

        Move operations, as instructed from APIs (e.g. request from DAV) could
        use this function.
        """
        raise NotImplementedError(repr(self))

    def create_child(self, cr, path, data=None):
        """ Create a regular file under this node
        """
        _logger.warning("Attempted to create a file under %r, not possible.", self)
        raise IOError(errno.EPERM, "Not allowed to create file(s) here.")

    def create_child_collection(self, cr, objname):
        """ Create a child collection (directory) under self
        """
        _logger.warning("Attempted to create a collection under %r, not possible.", self)
        raise IOError(errno.EPERM, "Not allowed to create folder(s) here.")

    def rm(self, cr):
        raise NotImplementedError(repr(self))

    def rmcol(self, cr):
        raise NotImplementedError(repr(self))

    def get_domain(self, cr, filters):
        # TODO Document
        return []

    def check_perms(self, perms):
        """ Check the permissions of the current node.

        @param perms either an integers of the bits to check, or
                a string with the permission letters

        Permissions of nodes are (in a unix way):
        1, x : allow descend into dir
        2, w : allow write into file, or modification to dir
        4, r : allow read of file, or listing of dir contents
        8, u : allow remove (unlink)
        """

        if isinstance(perms, str):
            pe2 = 0
            chars = { 'x': 1, 'w': 2, 'r': 4, 'u': 8 }
            for c in perms:
                pe2 = pe2 | chars[c]
            perms = pe2
        elif isinstance(perms, int):
            if perms < 0 or perms > 15:
                raise ValueError("Invalid permission bits.")
        else:
            raise ValueError("Invalid permission attribute.")

        return ((self.uidperms & perms) == perms)

class node_database(node_class):
    """ A node representing the database directory

    """
    our_type = 'database'
    def __init__(self, path=None, parent=False, context=None):
        if path is None:
            path = []
        super(node_database,self).__init__(path, parent, context)
        self.unixperms = 040750
        self.uidperms = 5

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

    def _child_get(self, cr, name=False, domain=None):
        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        where = [('parent_id','=', False), ('ressource_parent_type_id','=',False)]
        if name:
            where.append(('name','=',name))
            is_allowed = self.check_perms(1)
        else:
            is_allowed = self.check_perms(5)

        if not is_allowed:
            raise IOError(errno.EPERM, "Permission into directory denied.")

        if domain:
            where = where + domain
        ids = dirobj.search(cr, uid, where, context=ctx)
        res = []
        for dirr in dirobj.browse(cr, uid, ids, context=ctx):
            klass = dirr.get_node_class(dirr, context=ctx)
            res.append(klass(dirr.name, self, self.context,dirr))

        return res

    def _file_get(self, cr, nodename=False):
        res = []
        return res

    def _get_ttag(self, cr):
        return 'db-%s' % cr.dbname

def mkdosname(company_name, default='noname'):
    """ convert a string to a dos-like name"""
    if not company_name:
        return default
    badchars = ' !@#$%^`~*()+={}[];:\'"/?.<>'
    n = ''
    for c in company_name[:8]:
        n += (c in badchars and '_') or c
    return n

def _uid2unixperms(perms, has_owner):
    """ Convert the uidperms and the owner flag to full unix bits
    """
    res = 0
    if has_owner:
        res |= (perms & 0x07) << 6
        res |= (perms & 0x05) << 3
    elif perms & 0x02:
        res |= (perms & 0x07) << 6
        res |= (perms & 0x07) << 3
    else:
        res |= (perms & 0x07) << 6
        res |= (perms & 0x05) << 3
        res |= 0x05
    return res

class node_dir(node_database):
    our_type = 'collection'
    def __init__(self, path, parent, context, dirr, dctx=None):
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
        try:
            self.uuser = (dirr.user_id and dirr.user_id.login) or 'nobody'
        except Exception:
            self.uuser = 'nobody'
        self.ugroup = mkdosname(dirr.company_id and dirr.company_id.name, default='nogroup')
        self.uidperms = dirr.get_dir_permissions()
        self.unixperms = 040000 | _uid2unixperms(self.uidperms, dirr and dirr.user_id)
        if dctx:
            self.dctx.update(dctx)
        dc2 = self.context.context
        dc2.update(self.dctx)
        dc2['dir_id'] = self.dir_id
        self.displayname = dirr and dirr.name or False
        if dirr and dirr.dctx_ids:
            for dfld in dirr.dctx_ids:
                try:
                    self.dctx[dfld.field] = safe_eval(dfld.expr,dc2)
                except Exception,e:
                    print "Cannot eval %s." % dfld.expr
                    print e
                    pass

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        if not self.context == other.context:
            return False
        # Two directory nodes, for the same document.directory, may have a
        # different context! (dynamic folders)
        if self.dctx != other.dctx:
            return False
        return self.dir_id == other.dir_id

    def get_data(self, cr):
        #res = ''
        #for child in self.children(cr):
        #    res += child.get_data(cr)
        return None

    def _file_get(self, cr, nodename=False):
        res = super(node_dir,self)._file_get(cr, nodename)

        is_allowed = self.check_perms(nodename and 1 or 5)
        if not is_allowed:
            raise IOError(errno.EPERM, "Permission into directory denied.")

        cntobj = self.context._dirobj.pool.get('document.directory.content')
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        where = [('directory_id','=',self.dir_id) ]
        ids = cntobj.search(cr, uid, where, context=ctx)
        for content in cntobj.browse(cr, uid, ids, context=ctx):
            res3 = cntobj._file_get(cr, self, nodename, content)
            if res3:
                res.extend(res3)

        return res

    def _child_get(self, cr, name=None, domain=None):
        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        where = [('parent_id','=',self.dir_id)]
        if name:
            where.append(('name','=',name))
            is_allowed = self.check_perms(1)
        else:
            is_allowed = self.check_perms(5)

        if not is_allowed:
            raise IOError(errno.EPERM, "Permission into directory denied.")

        if not domain:
            domain = []

        where2 = where + domain + [('ressource_parent_type_id','=',False)]
        ids = dirobj.search(cr, uid, where2, context=ctx)
        res = []
        for dirr in dirobj.browse(cr, uid, ids, context=ctx):
            klass = dirr.get_node_class(dirr, context=ctx)
            res.append(klass(dirr.name, self, self.context,dirr))

        # Static directories should never return files with res_model/res_id
        # because static dirs are /never/ related to a record.
        # In fact, files related to some model and parented by the root dir
        # (the default), will NOT be accessible in the node system unless
        # a resource folder for that model exists (with resource_find_all=True).
        # Having resource attachments in a common folder is bad practice,
        # because they would be visible to all users, and their names may be
        # the same, conflicting.
        where += [('res_model', '=', False)]
        fil_obj = dirobj.pool.get('ir.attachment')
        ids = fil_obj.search(cr, uid, where, context=ctx)
        if ids:
            for fil in fil_obj.browse(cr, uid, ids, context=ctx):
                klass = self.context.node_file_class
                res.append(klass(fil.name, self, self.context, fil))
        return res

    def rmcol(self, cr):
        uid = self.context.uid
        directory = self.context._dirobj.browse(cr, uid, self.dir_id)
        res = False
        if not directory:
            raise OSError(2, 'Not such file or directory.')
        if not self.check_perms('u'):
            raise IOError(errno.EPERM,"Permission denied.")

        if directory._table_name=='document.directory':
            if self.children(cr):
                raise OSError(39, 'Directory not empty.')
            res = self.context._dirobj.unlink(cr, uid, [directory.id])
        else:
            raise OSError(1, 'Operation is not permitted.')
        return res

    def create_child_collection(self, cr, objname):
        object2 = False
        if not self.check_perms(2):
            raise IOError(errno.EPERM,"Permission denied.")

        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        obj = dirobj.browse(cr, uid, self.dir_id)
        if obj and (obj.type == 'ressource') and not object2:
            raise OSError(1, 'Operation is not permitted.')

        #objname = uri2[-1]
        val = {
                'name': objname,
                'ressource_parent_type_id': obj and obj.ressource_type_id.id or False,
                'ressource_id': object2 and object2.id or False,
                'parent_id' : obj and obj.id or False
        }

        return dirobj.create(cr, uid, val)

    def create_child(self, cr, path, data=None):
        """ API function to create a child file object and node
            Return the node_* created
        """
        if not self.check_perms(2):
            raise IOError(errno.EPERM,"Permission denied.")

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

        fil_id = fil_obj.create(cr, uid, val, context=ctx)
        fil = fil_obj.browse(cr, uid, fil_id, context=ctx)
        fnode = node_file(path, self, self.context, fil)
        if data is not None:
            fnode.set_data(cr, data, fil)
        return fnode

    def _get_ttag(self, cr):
        return 'dir-%d' % self.dir_id

    def move_to(self, cr, ndir_node, new_name=False, fil_obj=None, ndir_obj=None, in_write=False):
        """ Move directory. This operation is simple, since the present node is
        only used for static, simple directories.
            Note /may/ be called with ndir_node = None, to rename the document root.
        """
        if ndir_node and (ndir_node.context != self.context):
            raise NotImplementedError("Cannot move directories between contexts.")

        if (not self.check_perms('u')) or (not ndir_node.check_perms('w')):
            raise IOError(errno.EPERM,"Permission denied.")

        dir_obj = self.context._dirobj
        if not fil_obj:
            dbro = dir_obj.browse(cr, self.context.uid, self.dir_id, context=self.context.context)
        else:
            dbro = dir_obj
            assert dbro.id == self.dir_id

        if not dbro:
            raise IndexError("Cannot locate dir %d", self.dir_id)

        if (not self.parent) and ndir_node:
            if not dbro.parent_id:
                raise IOError(errno.EPERM, "Cannot move the root directory!")
            self.parent = self.context.get_dir_node(cr, dbro.parent_id)
            assert self.parent

        if self.parent != ndir_node:
            _logger.debug('Cannot move dir %r from %r to %r.', self, self.parent, ndir_node)
            raise NotImplementedError('Cannot move dir to another dir.')

        ret = {}
        if new_name and (new_name != dbro.name):
            if ndir_node.child(cr, new_name):
                raise IOError(errno.EEXIST, "Destination path already exists.")
            ret['name'] = new_name

        del dbro

        if not in_write:
            # We have to update the data ourselves
            if ret:
                ctx = self.context.context.copy()
                ctx['__from_node'] = True
                dir_obj.write(cr, self.context.uid, [self.dir_id,], ret, ctx)
            ret = True

        return ret

class node_res_dir(node_class):
    """ A folder containing dynamic folders
        A special sibling to node_dir, which does only contain dynamically
        created folders foreach resource in the foreign model.
        All folders should be of type node_res_obj and merely behave like
        node_dirs (with limited domain).
    """
    our_type = 'collection'
    res_obj_class = None
    def __init__(self, path, parent, context, dirr, dctx=None ):
        super(node_res_dir,self).__init__(path, parent, context)
        self.dir_id = dirr.id
        #todo: more info from dirr
        self.mimetype = 'application/x-directory'
                        # 'httpd/unix-directory'
        self.create_date = dirr.create_date
        # TODO: the write date should be MAX(file.write)..
        self.write_date = dirr.write_date or dirr.create_date
        self.content_length = 0
        try:
            self.uuser = (dirr.user_id and dirr.user_id.login) or 'nobody'
        except Exception:
            self.uuser = 'nobody'
        self.ugroup = mkdosname(dirr.company_id and dirr.company_id.name, default='nogroup')
        self.uidperms = dirr.get_dir_permissions()
        self.unixperms = 040000 | _uid2unixperms(self.uidperms, dirr and dirr.user_id)
        self.res_model = dirr.ressource_type_id and dirr.ressource_type_id.model or False
        self.resm_id = dirr.ressource_id
        self.res_find_all = dirr.resource_find_all
        self.namefield = dirr.resource_field.name or 'name'
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
            self.dctx_dict[dfld.field] = dfld.expr

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        if not self.context == other.context:
            return False
        # Two nodes, for the same document.directory, may have a
        # different context! (dynamic folders)
        if self.dctx != other.dctx:
            return False
        return self.dir_id == other.dir_id

    def children(self, cr, domain=None):
        return self._child_get(cr, domain=domain)

    def child(self, cr, name, domain=None):
        res = self._child_get(cr, name, domain=domain)
        if res:
            return res[0]
        return None

    def _child_get(self, cr, name=None, domain=None):
        """ return virtual children of resource, based on the
            foreign object.

            Note that many objects use NULL for a name, so we should
            better call the name_search(),name_get() set of methods
        """
        obj = self.context._dirobj.pool.get(self.res_model)
        if not obj:
            return []
        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        ctx.update(self.context.extra_ctx)
        where = []
        if self.domain:
            app = safe_eval(self.domain, ctx)
            if not app:
                pass
            elif isinstance(app, list):
                where.extend(app)
            elif isinstance(app, tuple):
                where.append(app)
            else:
                raise RuntimeError("Incorrect domain expr: %s." % self.domain)
        if self.resm_id:
            where.append(('id','=',self.resm_id))

        if name:
            # The =like character will match underscores against any characters
            # including the special ones that couldn't exist in a FTP/DAV request
            where.append((self.namefield,'=like',name.replace('\\','\\\\')))
            is_allowed = self.check_perms(1)
        else:
            is_allowed = self.check_perms(5)

        if not is_allowed:
            raise IOError(errno.EPERM,"Permission denied.")

        # print "Where clause for %s" % self.res_model, where
        if self.ressource_tree:
            object2 = False
            if self.resm_id:
                object2 = dirobj.pool.get(self.res_model).browse(cr, uid, self.resm_id) or False
            if obj._parent_name in obj.fields_get(cr, uid):
                where.append((obj._parent_name,'=',object2 and object2.id or False))

        resids = obj.search(cr, uid, where, context=ctx)
        res = []
        for bo in obj.browse(cr, uid, resids, context=ctx):
            if not bo:
                continue
            res_name = getattr(bo, self.namefield)
            if not res_name:
                continue
                # Yes! we can't do better but skip nameless records.

            # Escape the name for characters not supported in filenames
            res_name = res_name.replace('/','_') # any other weird char?

            if name and (res_name != ustr(name)):
                # we have matched _ to any character, but we only meant to match
                # the special ones.
                # Eg. 'a_c' will find 'abc', 'a/c', 'a_c', may only
                # return 'a/c' and 'a_c'
                continue

            res.append(self.res_obj_class(res_name, self.dir_id, self, self.context, self.res_model, bo))
        return res

    def _get_ttag(self, cr):
        return 'rdir-%d' % self.dir_id

class node_res_obj(node_class):
    """ A dynamically created folder.
        A special sibling to node_dir, which does only contain dynamically
        created folders foreach resource in the foreign model.
        All folders should be of type node_res_obj and merely behave like
        node_dirs (with limited domain).
        """
    our_type = 'collection'
    def __init__(self, path, dir_id, parent, context, res_model, res_bo, res_id=None):
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
        self.uidperms = parent.uidperms & 15
        self.unixperms = 040000 | _uid2unixperms(self.uidperms, True)
        self.uuser = parent.uuser
        self.ugroup = parent.ugroup
        self.res_model = res_model
        self.domain = parent.domain
        self.displayname = path
        self.dctx_dict = parent.dctx_dict
        if isinstance(parent, node_res_dir):
            self.res_find_all = parent.res_find_all
        else:
            self.res_find_all = False
        if res_bo:
            self.res_id = res_bo.id
            dc2 = self.context.context.copy()
            dc2.update(self.dctx)
            dc2['res_model'] = res_model
            dc2['res_id'] = res_bo.id
            dc2['this'] = res_bo
            for fld,expr in self.dctx_dict.items():
                try:
                    self.dctx[fld] = safe_eval(expr, dc2)
                except Exception,e:
                    print "Cannot eval %s for %s." % (expr, fld)
                    print e
                    pass
        else:
            self.res_id = res_id

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        if not self.context == other.context:
            return False
        if not self.res_model == other.res_model:
            return False
        if not self.res_id == other.res_id:
            return False
        if self.domain != other.domain:
            return False
        if self.res_find_all != other.res_find_all:
            return False
        if self.dctx != other.dctx:
            return False
        return self.dir_id == other.dir_id

    def children(self, cr, domain=None):
        return self._child_get(cr, domain=domain) + self._file_get(cr)

    def child(self, cr, name, domain=None):
        res = self._child_get(cr, name, domain=domain)
        if res:
            return res[0]
        res = self._file_get(cr, name)
        if res:
            return res[0]
        return None

    def _file_get(self, cr, nodename=False):
        res = []
        is_allowed = self.check_perms((nodename and 1) or 5)
        if not is_allowed:
            raise IOError(errno.EPERM,"Permission denied.")

        cntobj = self.context._dirobj.pool.get('document.directory.content')
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        where = [('directory_id','=',self.dir_id) ]
        #if self.domain:
        #    where.extend(self.domain)
        # print "res_obj file_get clause", where
        ids = cntobj.search(cr, uid, where, context=ctx)
        for content in cntobj.browse(cr, uid, ids, context=ctx):
            res3 = cntobj._file_get(cr, self, nodename, content, context=ctx)
            if res3:
                res.extend(res3)

        return res

    def get_dav_props_DEPR(self, cr):
        # Deprecated! (but document_ics must be cleaned, first)
        res = {}
        cntobj = self.context._dirobj.pool.get('document.directory.content')
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        where = [('directory_id','=',self.dir_id) ]
        ids = cntobj.search(cr, uid, where, context=ctx)
        for content in cntobj.browse(cr, uid, ids, context=ctx):
            if content.extension == '.ics': # FIXME: call the content class!
                res['http://groupdav.org/'] = ('resourcetype',)
        return res

    def get_dav_eprop_DEPR(self, cr, ns, prop):
        # Deprecated!
        if ns != 'http://groupdav.org/' or prop != 'resourcetype':
            _logger.warning("Who asks for %s:%s?" % (ns, prop))
            return None
        cntobj = self.context._dirobj.pool.get('document.directory.content')
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        where = [('directory_id','=',self.dir_id) ]
        ids = cntobj.search(cr,uid,where,context=ctx)
        for content in cntobj.browse(cr, uid, ids, context=ctx):
            # TODO: remove relic of GroupDAV
            if content.extension == '.ics': # FIXME: call the content class!
                return ('vevent-collection','http://groupdav.org/')
        return None

    def _child_get(self, cr, name=None, domain=None):
        dirobj = self.context._dirobj

        is_allowed = self.check_perms((name and 1) or 5)
        if not is_allowed:
            raise IOError(errno.EPERM,"Permission denied.")

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
            if name:
                where1.append(('name','=like',name.replace('\\','\\\\')))
            if obj._parent_name in obj.fields_get(cr, uid):
                where1.append((obj._parent_name, '=', self.res_id))
            namefield = directory.resource_field.name or 'name'
            resids = obj.search(cr, uid, where1, context=ctx)
            for bo in obj.browse(cr, uid, resids, context=ctx):
                if not bo:
                    continue
                res_name = getattr(bo, namefield)
                if not res_name:
                    continue
                res_name = res_name.replace('/', '_')
                if name and (res_name != ustr(name)):
                    continue
                # TODO Revise
                klass = directory.get_node_class(directory, dynamic=True, context=ctx)
                rnode = klass(res_name, dir_id=self.dir_id, parent=self, context=self.context,
                                res_model=self.res_model, res_bo=bo)
                rnode.res_find_all = self.res_find_all
                res.append(rnode)


        where2 = where + [('parent_id','=',self.dir_id) ]
        ids = dirobj.search(cr, uid, where2, context=ctx)
        bo = obj.browse(cr, uid, self.res_id, context=ctx)

        for dirr in dirobj.browse(cr, uid, ids, context=ctx):
            if name and (name != dirr.name):
                continue
            if dirr.type == 'directory':
                klass = dirr.get_node_class(dirr, dynamic=True, context=ctx)
                res.append(klass(dirr.name, dirr.id, self, self.context, self.res_model, res_bo = bo, res_id = self.res_id))
            elif dirr.type == 'ressource':
                # child resources can be controlled by properly set dctx
                klass = dirr.get_node_class(dirr, context=ctx)
                res.append(klass(dirr.name,self,self.context, dirr, {'active_id': self.res_id})) # bo?

        fil_obj = dirobj.pool.get('ir.attachment')
        if self.res_find_all:
            where2 = where
        where3 = where2 + [('res_model', '=', self.res_model), ('res_id','=',self.res_id)]
        # print "where clause for dir_obj", where3
        ids = fil_obj.search(cr, uid, where3, context=ctx)
        if ids:
            for fil in fil_obj.browse(cr, uid, ids, context=ctx):
                klass = self.context.node_file_class
                res.append(klass(fil.name, self, self.context, fil))


        # Get Child Ressource Directories
        if directory.ressource_type_id and directory.ressource_type_id.id:
            where4 = where + [('ressource_parent_type_id','=',directory.ressource_type_id.id)]
            where5 = where4 + ['|', ('ressource_id','=',0), ('ressource_id','=',self.res_id)]
            dirids = dirobj.search(cr,uid, where5)
            for dirr in dirobj.browse(cr, uid, dirids, context=ctx):
                if dirr.type == 'directory' and not dirr.parent_id:
                    klass = dirr.get_node_class(dirr, dynamic=True, context=ctx)
                    rnode = klass(dirr.name, dirr.id, self, self.context, self.res_model, res_bo = bo, res_id = self.res_id)
                    rnode.res_find_all = dirr.resource_find_all
                    res.append(rnode)
                if dirr.type == 'ressource':
                    klass = dirr.get_node_class(dirr, context=ctx)
                    rnode = klass(dirr.name, self, self.context, dirr, {'active_id': self.res_id})
                    rnode.res_find_all = dirr.resource_find_all
                    res.append(rnode)
        return res

    def create_child_collection(self, cr, objname):
        dirobj = self.context._dirobj
        is_allowed = self.check_perms(2)
        if not is_allowed:
            raise IOError(errno.EPERM,"Permission denied.")

        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        res_obj = dirobj.pool.get(self.res_model)

        object2 = res_obj.browse(cr, uid, self.res_id) or False

        obj = dirobj.browse(cr, uid, self.dir_id)
        if obj and (obj.type == 'ressource') and not object2:
            raise OSError(1, 'Operation is not permitted.')


        val = {
                'name': objname,
                'ressource_parent_type_id': obj and obj.ressource_type_id.id or False,
                'ressource_id': object2 and object2.id or False,
                'parent_id' : False,
                'resource_find_all': False,
        }
        if (obj and (obj.type in ('directory'))) or not object2:
            val['parent_id'] =  obj and obj.id or False

        return dirobj.create(cr, uid, val)

    def create_child(self, cr, path, data=None):
        """ API function to create a child file object and node
            Return the node_* created
        """
        is_allowed = self.check_perms(2)
        if not is_allowed:
            raise IOError(errno.EPERM,"Permission denied.")

        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        fil_obj=dirobj.pool.get('ir.attachment')
        val = {
            'name': path,
            'datas_fname': path,
            'res_model': self.res_model,
            'res_id': self.res_id,
            # Datas are not set here
        }
        if not self.res_find_all:
            val['parent_id'] = self.dir_id
        fil_id = fil_obj.create(cr, uid, val, context=ctx)
        fil = fil_obj.browse(cr, uid, fil_id, context=ctx)
        klass = self.context.node_file_class
        fnode = klass(path, self, self.context, fil)
        if data is not None:
            fnode.set_data(cr, data, fil)
        return fnode

    def _get_ttag(self, cr):
        return 'rodir-%d-%d' % (self.dir_id, self.res_id)

node_res_dir.res_obj_class = node_res_obj

class node_file(node_class):
    our_type = 'file'
    def __init__(self, path, parent, context, fil):
        super(node_file,self).__init__(path, parent,context)
        self.file_id = fil.id
        #todo: more info from ir_attachment
        if fil.file_type and '/' in fil.file_type:
            self.mimetype = str(fil.file_type)
        self.create_date = fil.create_date
        self.write_date = fil.write_date or fil.create_date
        self.content_length = fil.file_size
        self.displayname = fil.name

        self.uidperms = 14
        if parent:
            if not parent.check_perms('x'):
                self.uidperms = 0
            elif not parent.check_perms('w'):
                self.uidperms = 4

        try:
            self.uuser = (fil.user_id and fil.user_id.login) or 'nobody'
        except Exception:
            self.uuser = 'nobody'
        self.ugroup = mkdosname(fil.company_id and fil.company_id.name, default='nogroup')

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        if not self.context == other.context:
            return False
        if self.dctx != other.dctx:
            return False
        return self.file_id == other.file_id

    def open_data(self, cr, mode):
        if not self.check_perms(4):
            raise IOError(errno.EPERM, "Permission denied.")

        stobj = self.context._dirobj.pool.get('document.storage')
        return stobj.get_file(cr, self.context.uid, None, self, mode=mode, context=self.context.context)

    def rm(self, cr):
        uid = self.context.uid
        if not self.check_perms(8):
            raise IOError(errno.EPERM, "Permission denied.")
        document_obj = self.context._dirobj.pool.get('ir.attachment')
        if self.type in ('collection','database'):
            return False
        document = document_obj.browse(cr, uid, self.file_id, context=self.context.context)
        res = False
        if document and document._table_name == 'ir.attachment':
            res = document_obj.unlink(cr, uid, [document.id])
        return res

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

    def get_data(self, cr, fil_obj=None):
        """ Retrieve the data for some file.
            fil_obj may optionally be specified, and should be a browse object
            for the file. This is useful when the caller has already initiated
            the browse object. """
        if not self.check_perms(4):
            raise IOError(errno.EPERM, "Permission denied.")

        stobj = self.context._dirobj.pool.get('document.storage')
        return stobj.get_data(cr, self.context.uid, None, self,self.context.context, fil_obj)

    def get_data_len(self, cr, fil_obj=None):
        bin_size = self.context.context.get('bin_size', False)
        if bin_size and not self.content_length:
            self.content_length = fil_obj.db_datas
        return self.content_length

    def set_data(self, cr, data, fil_obj=None):
        """ Store data at some file.
            fil_obj may optionally be specified, and should be a browse object
            for the file. This is useful when the caller has already initiated
            the browse object. """
        if not self.check_perms(2):
            raise IOError(errno.EPERM, "Permission denied.")

        stobj = self.context._dirobj.pool.get('document.storage')
        return stobj.set_data(cr, self.context.uid, None, self, data, self.context.context, fil_obj)

    def _get_ttag(self, cr):
        return 'file-%d' % self.file_id

    def move_to(self, cr, ndir_node, new_name=False, fil_obj=None, ndir_obj=None, in_write=False):
        if ndir_node and ndir_node.context != self.context:
            raise NotImplementedError("Cannot move files between contexts.")

        if (not self.check_perms(8)) and ndir_node.check_perms(2):
            raise IOError(errno.EPERM, "Permission denied.")

        doc_obj = self.context._dirobj.pool.get('ir.attachment')
        if not fil_obj:
            dbro = doc_obj.browse(cr, self.context.uid, self.file_id, context=self.context.context)
        else:
            dbro = fil_obj
            assert dbro.id == self.file_id, "%s != %s for %r." % (dbro.id, self.file_id, self)

        if not dbro:
            raise IndexError("Cannot locate doc %d.", self.file_id)

        if (not self.parent):
            # there *must* be a parent node for this one
            self.parent = self.context.get_dir_node(cr, dbro.parent_id)
            assert self.parent

        ret = {}
        if ndir_node and self.parent != ndir_node:
            if not (isinstance(self.parent, node_dir) and isinstance(ndir_node, node_dir)):
                _logger.debug('Cannot move file %r from %r to %r.', self, self.parent, ndir_node)
                raise NotImplementedError('Cannot move files between dynamic folders.')

            if not ndir_obj:
                ndir_obj = self.context._dirobj.browse(cr, self.context.uid, \
                        ndir_node.dir_id, context=self.context.context)

            assert ndir_obj.id == ndir_node.dir_id

            r2 = { 'parent_id': ndir_obj.id }
            ret.update(r2)

        if new_name and (new_name != dbro.name):
            if len(ret):
                raise NotImplementedError("Cannot rename and move.") # TODO
            r2 = { 'name': new_name, 'datas_fname': new_name }
            ret.update(r2)

        del dbro

        if not in_write:
            # We have to update the data ourselves
            if ret:
                ctx = self.context.context.copy()
                ctx['__from_node'] = True
                doc_obj.write(cr, self.context.uid, [self.file_id,], ret, ctx )
            ret = True

        return ret

class node_content(node_class):
    our_type = 'content'
    def __init__(self, path, parent, context, cnt, dctx=None, act_id=None):
        super(node_content,self).__init__(path, parent,context)
        self.cnt_id = cnt.id
        self.create_date = False
        self.write_date = False
        self.content_length = False
        self.unixperms = 0640
        if parent:
            self.uidperms = parent.uidperms & 14
            self.uuser = parent.uuser
            self.ugroup = parent.ugroup

        self.extension = cnt.extension
        self.report_id = cnt.report_id and cnt.report_id.id
        #self.mimetype = cnt.extension.
        self.displayname = path
        if dctx:
           self.dctx.update(dctx)
        self.act_id = act_id

    def fill_fields(self, cr, dctx=None):
        """ Try to read the object and fill missing fields, like mimetype,
            dates etc.
            This function must be different from the constructor, because
            it uses the db cursor.
        """

        cr.execute('SELECT DISTINCT mimetype FROM document_directory_content_type WHERE active AND code = %s;',
                (self.extension,))
        res = cr.fetchall()
        if res and res[0][0]:
            self.mimetype = str(res[0][0])

    def get_data(self, cr, fil_obj=None):
        cntobj = self.context._dirobj.pool.get('document.directory.content')
        if not self.check_perms(4):
            raise IOError(errno.EPERM, "Permission denied.")

        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        data = cntobj.process_read(cr, self.context.uid, self, ctx)
        if data:
            self.content_length = len(data)
        return data

    def open_data(self, cr, mode):
        if mode.endswith('b'):
            mode = mode[:-1]
        if mode in ('r', 'w'):
            cperms = mode[:1]
        elif mode in ('r+', 'w+'):
            cperms = 'rw'
        else:
            raise IOError(errno.EINVAL, "Cannot open at mode %s." % mode)

        if not self.check_perms(cperms):
            raise IOError(errno.EPERM, "Permission denied.")

        ctx = self.context.context.copy()
        ctx.update(self.dctx)

        return nodefd_content(self, cr, mode, ctx)

    def get_data_len(self, cr, fil_obj=None):
        # FIXME : here, we actually generate the content twice!!
        # we should have cached the generated content, but it is
        # not advisable to do keep it in memory, until we have a cache
        # expiration logic.
        if not self.content_length:
            self.get_data(cr,fil_obj)
        return self.content_length

    def set_data(self, cr, data, fil_obj=None):
        cntobj = self.context._dirobj.pool.get('document.directory.content')
        if not self.check_perms(2):
            raise IOError(errno.EPERM, "Permission denied.")

        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        return cntobj.process_write(cr, self.context.uid, self, data, ctx)

    def _get_ttag(self, cr):
        return 'cnt-%d%s' % (self.cnt_id,(self.act_id and ('-' + str(self.act_id))) or '')

    def get_dav_resourcetype(self, cr):
        return ''

class node_descriptor(object):
    """A file-like interface to the data contents of a node.

       This class is NOT a node, but an /open descriptor/ for some
       node. It can hold references to a cursor or a file object,
       because the life of a node_descriptor will be the open period
       of the data.
       It should also take care of locking, with any native mechanism
       or using the db.
       For the implementation, it would be OK just to wrap around file,
       StringIO or similar class. The node_descriptor is only needed to
       provide the link to the parent /node/ object.
    """

    def __init__(self, parent):
        assert isinstance(parent, node_class)
        self.name = parent.displayname
        self.__parent = parent

    def _get_parent(self):
        return self.__parent

    def open(self, **kwargs):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def read(self, size=None):
        raise NotImplementedError

    def seek(self, offset, whence=None):
        raise NotImplementedError

    def tell(self):
        raise NotImplementedError

    def write(self, str):
        raise NotImplementedError

    def size(self):
        raise NotImplementedError

    def __len__(self):
        return self.size()

    def __nonzero__(self):
        """ Ensure that a node_descriptor will never equal False

            Since we do define __len__ and __iter__ for us, we must avoid
            being regarded as non-true objects.
        """
        return True

    def next(self, str):
        raise NotImplementedError

class nodefd_content(StringIO, node_descriptor):
    """ A descriptor to content nodes
    """
    def __init__(self, parent, cr, mode, ctx):
        node_descriptor.__init__(self, parent)
        self._context=ctx
        self._size = 0L

        if mode in ('r', 'r+'):
            cntobj = parent.context._dirobj.pool.get('document.directory.content')
            data = cntobj.process_read(cr, parent.context.uid, parent, ctx)
            if data:
                self._size = len(data)
                parent.content_length = len(data)
            StringIO.__init__(self, data)
        elif mode in ('w', 'w+'):
            StringIO.__init__(self, None)
            # at write, we start at 0 (= overwrite), but have the original
            # data available, in case of a seek()
        elif mode == 'a':
            StringIO.__init__(self, None)
        else:
            _logger.error("Incorrect mode %s is specified.", mode)
            raise IOError(errno.EINVAL, "Invalid file mode.")
        self.mode = mode

    def size(self):
        return self._size

    def close(self):
        # we now open a *separate* cursor, to update the data.
        # FIXME: this may be improved, for concurrency handling
        if self.mode == 'r':
            StringIO.close(self)
            return

        par = self._get_parent()
        uid = par.context.uid
        cr = pooler.get_db(par.context.dbname).cursor()
        try:
            if self.mode in ('w', 'w+', 'r+'):
                data = self.getvalue()
                cntobj = par.context._dirobj.pool.get('document.directory.content')
                cntobj.process_write(cr, uid, par, data, par.context.context)
            elif self.mode == 'a':
                raise NotImplementedError
            cr.commit()
        except Exception:
            _logger.exception('Cannot update db content #%d for close.', par.cnt_id)
            raise
        finally:
            cr.close()
        StringIO.close(self)

class nodefd_static(StringIO, node_descriptor):
    """ A descriptor to nodes with static data.
    """
    def __init__(self, parent, cr, mode, ctx=None):
        node_descriptor.__init__(self, parent)
        self._context=ctx
        self._size = 0L

        if mode in ('r', 'r+'):
            data = parent.get_data(cr)
            if data:
                self._size = len(data)
                parent.content_length = len(data)
            StringIO.__init__(self, data)
        elif mode in ('w', 'w+'):
            StringIO.__init__(self, None)
            # at write, we start at 0 (= overwrite), but have the original
            # data available, in case of a seek()
        elif mode == 'a':
            StringIO.__init__(self, None)
        else:
            _logger.error("Incorrect mode %s is specified.", mode)
            raise IOError(errno.EINVAL, "Invalid file mode.")
        self.mode = mode

    def size(self):
        return self._size

    def close(self):
        # we now open a *separate* cursor, to update the data.
        # FIXME: this may be improved, for concurrency handling
        if self.mode == 'r':
            StringIO.close(self)
            return

        par = self._get_parent()
        # uid = par.context.uid
        cr = pooler.get_db(par.context.dbname).cursor()
        try:
            if self.mode in ('w', 'w+', 'r+'):
                data = self.getvalue()
                par.set_data(cr, data)
            elif self.mode == 'a':
                raise NotImplementedError
            cr.commit()
        except Exception:
            _logger.exception('Cannot update db content #%d for close.', par.cnt_id)
            raise
        finally:
            cr.close()
        StringIO.close(self)

class nodefd_db(StringIO, node_descriptor):
    """ A descriptor to db data
    """
    def __init__(self, parent, ira_browse, mode):
        node_descriptor.__init__(self, parent)
        self._size = 0L
        if mode.endswith('b'):
            mode = mode[:-1]

        if mode in ('r', 'r+'):
            data = ira_browse.datas
            if data:
                data = data.decode('base64')
                self._size = len(data)
            StringIO.__init__(self, data)
        elif mode in ('w', 'w+'):
            StringIO.__init__(self, None)
            # at write, we start at 0 (= overwrite), but have the original
            # data available, in case of a seek()
        elif mode == 'a':
            StringIO.__init__(self, None)
        else:
            _logger.error("Incorrect mode %s is specified.", mode)
            raise IOError(errno.EINVAL, "Invalid file mode.")
        self.mode = mode

    def size(self):
        return self._size

    def close(self):
        # we now open a *separate* cursor, to update the data.
        # FIXME: this may be improved, for concurrency handling
        par = self._get_parent()
        # uid = par.context.uid
        registry = openerp.modules.registry.RegistryManager.get(par.context.dbname)
        with registry.cursor() as cr:
            data = self.getvalue().encode('base64')
            if self.mode in ('w', 'w+', 'r+'):
                registry.get('ir.attachment').write(cr, 1, par.file_id, {'datas': data})
            cr.commit()
        StringIO.close(self)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
