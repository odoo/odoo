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

#from psycopg2 import Binary
#from tools import config
import tools
from tools.translate import _
import nodes
import logging

_logger = logging.getLogger(__name__)

DMS_ROOT_PATH = tools.config.get('document_path', os.path.join(tools.config['root_path'], 'filestore'))

class document_file(osv.osv):
    _inherit = 'ir.attachment'
    _rec_name = 'name'

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
            raise NotImplementedError("Ids are just there by convention, please do not use it.")

        cr.execute("UPDATE ir_attachment SET parent_id = %s WHERE parent_id IS NULL", (parent_id,))

        cr.execute("UPDATE ir_attachment SET file_size=length(db_datas) WHERE file_size = 0 and type = 'binary'")

        cr.execute("ALTER TABLE ir_attachment ALTER parent_id SET NOT NULL")

        return True

    _columns = {
        # Columns from ir.attachment:
        'write_date': fields.datetime('Date Modified', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True),
        # Fields of document:
        'user_id': fields.many2one('res.users', 'Owner', select=1),
        'parent_id': fields.many2one('document.directory', 'Directory', select=1, required=True, change_default=True),
        'index_content': fields.text('Indexed Content'),
        'partner_id':fields.many2one('res.partner', 'Partner', select=1),
        'file_size': fields.integer('File Size', required=True),
        'file_type': fields.char('Content Type', size=128),
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

    def onchange_file(self, cr, uid, ids, datas_fname=False, context=None):
        res = {'value':{}}
        if datas_fname:
            res['value'].update({'name': datas_fname})
        return res

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
            default.update(name=_("%s (copy)") % (name))
        return super(document_file, self).copy(cr, uid, id, default, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        result = False
        if not isinstance(ids, list):
            ids = [ids]
        res = self.search(cr, uid, [('id', 'in', ids)])
        if not len(res):
            return False

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

        return super(document_file, self).create(cr, uid, vals, context)

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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
