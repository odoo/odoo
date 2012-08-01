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
from osv import osv, fields
import os

# from psycopg2 import Binary
#from tools import config
import tools
from tools.translate import _
import nodes
import logging

_logger = logging.getLogger(__name__)

DMS_ROOT_PATH = tools.config.get('document_path', os.path.join(tools.config['root_path'], 'filestore'))

class document_file(osv.osv):
    _inherit = 'ir.attachment'
    _rec_name = 'datas_fname'
   
   
    def _attach_parent_id(self, cr, uid, ids=None, context=None):
        """Migrate ir.attachments to the document module.

        When the 'document' module is loaded on a db that has had plain attachments,
        they will need to be attached to some parent folder, and be converted from
        base64-in-bytea to raw-in-bytea format.
        This function performs the internal migration, once and forever, for these
        attachments. It cannot be done through the nominal ORM maintenance code,
        because the root folder is only created after the document_data.xml file
        is loaded.
        It also establishes the parent_id NOT NULL constraint that ir.attachment
        should have had (but would have failed if plain attachments contained null
        values).
        It also updates the  File Size for the previously created attachments.
        """

        parent_id = self.pool.get('document.directory')._get_root_directory(cr,uid)
        if not parent_id:
            _logger.warning("at _attach_parent_id(), still not able to set the parent!")
            return False

        if ids is not None:
            raise NotImplementedError("Ids is just there by convention,please do not use it.")

        cr.execute("UPDATE ir_attachment " \
                    "SET parent_id = %s, db_datas = decode(encode(db_datas,'escape'), 'base64') " \
                    "WHERE parent_id IS NULL", (parent_id,))

        cr.execute("UPDATE ir_attachment SET file_size=length(db_datas) WHERE file_size = 0 and type = 'binary'")

        cr.execute("ALTER TABLE ir_attachment ALTER parent_id SET NOT NULL")

        return True

    def _get_filestore(self, cr):
        return os.path.join(DMS_ROOT_PATH, cr.dbname)

    def _data_get(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        fbrl = self.browse(cr, uid, ids, context=context)
        nctx = nodes.get_node_context(cr, uid, context={})
        # nctx will /not/ inherit the caller's context. Most of
        # it would be useless, anyway (like active_id, active_model,
        # bin_size etc.)
        result = {}
        bin_size = context.get('bin_size', False)
        for fbro in fbrl:
            fnode = nodes.node_file(None, None, nctx, fbro)
            if not bin_size:
                    data = fnode.get_data(cr, fbro)
                    result[fbro.id] = base64.encodestring(data or '')
            else:
                    result[fbro.id] = fnode.get_data_len(cr, fbro)

        return result

    #
    # This code can be improved
    #
    def _data_set(self, cr, uid, id, name, value, arg, context=None):
        if not value:
            return True
        fbro = self.browse(cr, uid, id, context=context)
        nctx = nodes.get_node_context(cr, uid, context={})
        fnode = nodes.node_file(None, None, nctx, fbro)
        res = fnode.set_data(cr, base64.decodestring(value), fbro)
        return res

    _columns = {
        # Columns from ir.attachment:
        'create_date': fields.datetime('Date Created', readonly=True),
        'create_uid':  fields.many2one('res.users', 'Creator', readonly=True),
        'write_date': fields.datetime('Date Modified', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True),
        'res_model': fields.char('Attached Model', size=64, readonly=True, change_default=True),
        'res_id': fields.integer('Attached ID', readonly=True),

        # If ir.attachment contained any data before document is installed, preserve
        # the data, don't drop the column!
        'db_datas': fields.binary('Data', oldname='datas'),
        'datas': fields.function(_data_get, fnct_inv=_data_set, string='File Content', type="binary", nodrop=True),

        # Fields of document:
        'user_id': fields.many2one('res.users', 'Owner', select=1),
        # 'group_ids': fields.many2many('res.groups', 'document_group_rel', 'item_id', 'group_id', 'Groups'),
        # the directory id now is mandatory. It can still be computed automatically.
        'parent_id': fields.many2one('document.directory', 'Directory', select=1, required=True, change_default=True),
        'index_content': fields.text('Indexed Content'),
        'partner_id':fields.many2one('res.partner', 'Partner', select=1),
        'file_size': fields.integer('File Size', required=True),
        'file_type': fields.char('Content Type', size=128),

        # fields used for file storage
        'store_fname': fields.char('Stored Filename', size=200),
    }
    _order = "id desc"

    def __get_def_directory(self, cr, uid, context=None):
        dirobj = self.pool.get('document.directory')
        return dirobj._get_root_directory(cr, uid, context)

    _defaults = {
        'user_id': lambda self, cr, uid, ctx:uid,
        'parent_id': __get_def_directory,
        'file_size': lambda self, cr, uid, ctx:0,
    }
    _sql_constraints = [
        # filename_uniq is not possible in pure SQL
    ]
    def _check_duplication(self, cr, uid, vals, ids=[], op='create'):
        name = vals.get('name', False)
        parent_id = vals.get('parent_id', False)
        res_model = vals.get('res_model', False)
        res_id = vals.get('res_id', 0)
        if op == 'write':
            for file in self.browse(cr, uid, ids): # FIXME fields_only
                if not name:
                    name = file.name
                if not parent_id:
                    parent_id = file.parent_id and file.parent_id.id or False
                if not res_model:
                    res_model = file.res_model and file.res_model or False
                if not res_id:
                    res_id = file.res_id and file.res_id or 0
                res = self.search(cr, uid, [('id', '<>', file.id), ('name', '=', name), ('parent_id', '=', parent_id), ('res_model', '=', res_model), ('res_id', '=', res_id)])
                if len(res):
                    return False
        if op == 'create':
            res = self.search(cr, uid, [('name', '=', name), ('parent_id', '=', parent_id), ('res_id', '=', res_id), ('res_model', '=', res_model)])
            if len(res):
                return False
        return True

    def check(self, cr, uid, ids, mode, context=None, values=None):
        """Check access wrt. res_model, relax the rule of ir.attachment parent

        With 'document' installed, everybody will have access to attachments of
        any resources they can *read*.
        """
        return super(document_file, self).check(cr, uid, ids, mode='read',
                                            context=context, values=values)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # Grab ids, bypassing 'count'
        ids = super(document_file, self).search(cr, uid, args, offset=offset,
                                                limit=limit, order=order,
                                                context=context, count=False)
        if not ids:
            return 0 if count else []

        # Filter out documents that are in directories that the user is not allowed to read.
        # Must use pure SQL to avoid access rules exceptions (we want to remove the records,
        # not fail), and the records have been filtered in parent's search() anyway.
        cr.execute('SELECT id, parent_id from "%s" WHERE id in %%s' % self._table, (tuple(ids),))
        doc_pairs = cr.fetchall()
        parent_ids = set(zip(*doc_pairs)[1])
        visible_parent_ids = self.pool.get('document.directory').search(cr, uid, [('id', 'in', list(parent_ids))])
        disallowed_parents = parent_ids.difference(visible_parent_ids)
        for doc_id, parent_id in doc_pairs:
            if parent_id in disallowed_parents:
                ids.remove(doc_id)
        return len(ids) if count else ids


    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        if 'name' not in default:
            name = self.read(cr, uid, [id], ['name'])[0]['name']
            default.update({'name': name + " " + _("(copy)")})
        return super(document_file, self).copy(cr, uid, id, default, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        result = False
        if not isinstance(ids, list):
            ids = [ids]
        res = self.search(cr, uid, [('id', 'in', ids)])
        if not len(res):
            return False
        if not self._check_duplication(cr, uid, vals, ids, 'write'):
            raise osv.except_osv(_('ValidateError'), _('File name must be unique!'))

        # if nodes call this write(), they must skip the code below
        from_node = context and context.get('__from_node', False)
        if (('parent_id' in vals) or ('name' in vals)) and not from_node:
            # perhaps this file is renaming or changing directory
            nctx = nodes.get_node_context(cr,uid,context={})
            dirobj = self.pool.get('document.directory')
            if 'parent_id' in vals:
                dbro = dirobj.browse(cr, uid, vals['parent_id'], context=context)
                dnode = nctx.get_dir_node(cr, dbro)
            else:
                dbro = None
                dnode = None
            ids2 = []
            for fbro in self.browse(cr, uid, ids, context=context):
                if ('parent_id' not in vals or fbro.parent_id.id == vals['parent_id']) \
                    and ('name' not in vals or fbro.name == vals['name']):
                        ids2.append(fbro.id)
                        continue
                fnode = nctx.get_file_node(cr, fbro)
                res = fnode.move_to(cr, dnode or fnode.parent, vals.get('name', fbro.name), fbro, dbro, True)
                if isinstance(res, dict):
                    vals2 = vals.copy()
                    vals2.update(res)
                    wid = res.get('id', fbro.id)
                    result = super(document_file,self).write(cr,uid,wid,vals2,context=context)
                    # TODO: how to handle/merge several results?
                elif res == True:
                    ids2.append(fbro.id)
                elif res == False:
                    pass
            ids = ids2
        if 'file_size' in vals: # only write that field using direct SQL calls
            del vals['file_size']
        if ids and vals:
            result = super(document_file,self).write(cr, uid, ids, vals, context=context)
        return result

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        vals['parent_id'] = context.get('parent_id', False) or vals.get('parent_id', False)
        if not vals['parent_id']:
            vals['parent_id'] = self.pool.get('document.directory')._get_root_directory(cr,uid, context)
        if not vals.get('res_id', False) and context.get('default_res_id', False):
            vals['res_id'] = context.get('default_res_id', False)
        if not vals.get('res_model', False) and context.get('default_res_model', False):
            vals['res_model'] = context.get('default_res_model', False)
        if vals.get('res_id', False) and vals.get('res_model', False) \
                and not vals.get('partner_id', False):
            vals['partner_id'] = self.__get_partner_id(cr, uid, \
                vals['res_model'], vals['res_id'], context)

        datas = None
        if vals.get('link', False) :
            import urllib
            datas = base64.encodestring(urllib.urlopen(vals['link']).read())
        else:
            datas = vals.get('datas', False)

        if datas:
            vals['file_size'] = len(datas)
        else:
            if vals.get('file_size'):
                del vals['file_size']
        result = self._check_duplication(cr, uid, vals)
        if not result:
            domain = [
                ('res_id', '=', vals['res_id']),
                ('res_model', '=', vals['res_model']),
                ('datas_fname', '=', vals['datas_fname']),
            ]
            attach_ids = self.search(cr, uid, domain, context=context)
            super(document_file, self).write(cr, uid, attach_ids, 
                                             {'datas' : vals['datas']},
                                             context=context)
            result = attach_ids[0]
        else:
            #raise osv.except_osv(_('ValidateError'), _('File name must be unique!'))
            result = super(document_file, self).create(cr, uid, vals, context)
        return result

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

    def unlink(self, cr, uid, ids, context=None):
        stor = self.pool.get('document.storage')
        unres = []
        # We have to do the unlink in 2 stages: prepare a list of actual
        # files to be unlinked, update the db (safer to do first, can be
        # rolled back) and then unlink the files. The list wouldn't exist
        # after we discard the objects
        ids = self.search(cr, uid, [('id','in',ids)])
        for f in self.browse(cr, uid, ids, context=context):
            # TODO: update the node cache
            par = f.parent_id
            storage_id = None
            while par:
                if par.storage_id:
                    storage_id = par.storage_id
                    break
                par = par.parent_id
            #assert storage_id, "Strange, found file #%s w/o storage!" % f.id #TOCHECK: after run yml, it's fail
            if storage_id:
                r = stor.prepare_unlink(cr, uid, storage_id, f)
                if r:
                    unres.append(r)
            else:
                self.loggerdoc.warning("Unlinking attachment #%s %s that has no storage.",
                                                f.id, f.name)
        res = super(document_file, self).unlink(cr, uid, ids, context)
        stor.do_unlink(cr, uid, unres)
        return res

document_file()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
