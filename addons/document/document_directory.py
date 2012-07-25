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


from osv import osv, fields
from osv.orm import except_orm
import logging
import nodes
from tools.translate import _
_logger = logging.getLogger(__name__)
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
        'domain': fields.char('Domain', size=128, help="Use a domain if you want to apply an automatic filter on visible resources."),
        'user_id': fields.many2one('res.users', 'Owner'),
        'storage_id': fields.many2one('document.storage', 'Storage', change_default=True),
        'group_ids': fields.many2many('res.groups', 'document_directory_group_rel', 'item_id', 'group_id', 'Groups'),
        'parent_id': fields.many2one('document.directory', 'Parent Directory', select=1, change_default=True),
        'child_ids': fields.one2many('document.directory', 'parent_id', 'Children'),
        'file_ids': fields.one2many('ir.attachment', 'parent_id', 'Files'),
        'content_ids': fields.one2many('document.directory.content', 'directory_id', 'Virtual Files'),
        'type': fields.selection([
            ('directory','Static Directory'),
            ('ressource','Folders per resource'),
            ],
            'Type', required=True, select=1, change_default=True,
            help="Each directory can either have the type Static or be linked to another resource. A static directory, as with Operating Systems, is the classic directory that can contain a set of files. The directories linked to systems resources automatically possess sub-directories for each of resource types defined in the parent directory."),
        'ressource_type_id': fields.many2one('ir.model', 'Resource model', change_default=True,
            help="Select an object here and there will be one folder per record of that resource."),
        'resource_field': fields.many2one('ir.model.fields', 'Name field', help='Field to be used as name on resource directories. If empty, the "name" will be used.'),
        'resource_find_all': fields.boolean('Find all resources', required=True,
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


    def _get_root_directory(self, cr,uid, context=None):
        objid=self.pool.get('ir.model.data')
        try:
            mid = objid._get_id(cr, uid, 'document', 'dir_root')
            if not mid:
                return False
            root_id = objid.read(cr, uid, mid, ['res_id'])['res_id']
            return root_id
        except Exception, e:
            
            _logger.warning('Cannot set directory root:'+ str(e))
            return False
        return objid.browse(cr, uid, mid, context=context).res_id

    def _get_def_storage(self, cr, uid, context=None):
        if context and context.has_key('default_parent_id'):
                # Use the same storage as the parent..
                diro = self.browse(cr, uid, context['default_parent_id'])
                if diro.storage_id:
                        return diro.storage_id.id
        objid=self.pool.get('ir.model.data')
        try:
                mid =  objid._get_id(cr, uid, 'document', 'storage_default')
                return objid.browse(cr, uid, mid, context=context).res_id
        except Exception:
                return None

    _defaults = {
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'document.directory', context=c),
        'user_id': lambda self,cr,uid,ctx: uid,
        'domain': '[]',
        'type': 'directory',
        'ressource_id': 0,
        'storage_id': _get_def_storage, # Still, it is bad practice to set it everywhere.
        'resource_find_all': True,
    }
    _sql_constraints = [
        ('dirname_uniq', 'unique (name,parent_id,ressource_id,ressource_parent_type_id)', 'The directory name must be unique !'),
        ('no_selfparent', 'check(parent_id <> id)', 'Directory cannot be parent of itself!'),
        ('dir_parented', 'check(parent_id IS NOT NULL OR storage_id IS NOT NULL)', 'Directory must have a parent or a storage.')
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
        (_check_recursion, 'Error! You can not create recursive Directories.', ['parent_id'])
    ]

    def __init__(self, *args, **kwargs):
        super(document_directory, self).__init__(*args, **kwargs)

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

        return nodes.get_node_context(cr, uid, context).get_uri(cr, uri)

    def get_node_class(self, cr, uid, ids, dbro=None, dynamic=False, context=None):
        """Retrieve the class of nodes for this directory
           
           This function can be overriden by inherited classes ;)
           @param dbro The browse object, if caller already has it
        """
        if dbro is None:
            dbro = self.browse(cr, uid, ids, context=context)

        if dynamic:
            return nodes.node_res_obj
        elif dbro.type == 'directory':
            return nodes.node_dir
        elif dbro.type == 'ressource':
            return nodes.node_res_dir
        else:
            raise ValueError("dir node for %s type!", dbro.type)

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

    def _locate_child(self, cr, uid, root_id, uri,nparent, ncontext):
        """ try to locate the node in uri,
            Return a tuple (node_dir, remaining_path)
        """
        return (nodes.node_database(context=ncontext), uri)

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default ={}
        name = self.read(cr, uid, [id])[0]['name']
        default.update({'name': name+ " (copy)"})
        return super(document_directory,self).copy(cr, uid, id, default, context=context)

    def _check_duplication(self, cr, uid, vals, ids=[], op='create'):
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

    # TODO def unlink(...

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
    _description = 'Directory Dynamic Context'
    _columns = {
        'dir_id': fields.many2one('document.directory', 'Directory', required=True, ondelete="cascade"),
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
