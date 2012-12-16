# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (C) P. Christeas, 2009, all rights reserved
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

from osv import osv, fields
import os
import tools
import base64
import errno
import logging
import shutil
from StringIO import StringIO
import psycopg2
from tools.misc import ustr
from tools.translate import _
from osv.orm import except_orm
import random
import string
import pooler
import nodes
from content_index import cntIndex
_logger = logging.getLogger(__name__)

""" The algorithm of data storage

We have to consider 3 cases of data /retrieval/:
 Given (context,path) we need to access the file (aka. node).
 given (directory, context), we need one of its children (for listings, views)
 given (ir.attachment, context), we need its data and metadata (node).

For data /storage/ we have the cases:
 Have (ir.attachment, context), we modify the file (save, update, rename etc).
 Have (directory, context), we create a file.
 Have (path, context), we create or modify a file.

Note that in all above cases, we don't explicitly choose the storage media,
but always require a context to be present.

Note that a node will not always have a corresponding ir.attachment. Dynamic
nodes, for once, won't. Their metadata will be computed by the parent storage
media + directory.

The algorithm says that in any of the above cases, our first goal is to locate
the node for any combination of search criteria. It would be wise NOT to
represent each node in the path (like node[/] + node[/dir1] + node[/dir1/dir2])
but directly jump to the end node (like node[/dir1/dir2]) whenever possible.

We also contain all the parenting loop code in one function. This is intentional,
because one day this will be optimized in the db (Pg 8.4).

"""

class nodefd_db(StringIO, nodes.node_descriptor):
    """ A descriptor to db data
    """
    def __init__(self, parent, ira_browse, mode):
        nodes.node_descriptor.__init__(self, parent)
        self._size = 0L
        if mode.endswith('b'):
            mode = mode[:-1]

        if mode in ('r', 'r+'):
            data = ira_browse.datas
            if data:
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
        cr = pooler.get_db(par.context.dbname).cursor()
        try:
            if self.mode in ('w', 'w+', 'r+'):
                data = self.getvalue()
                icont = ''
                mime = ''
                filename = par.path
                if isinstance(filename, (tuple, list)):
                    filename = '/'.join(filename)

                try:
                    mime, icont = cntIndex.doIndex(data, filename=filename,
                            content_type=None, realfname=None)
                except Exception:
                    _logger.debug('Cannot index file:', exc_info=True)
                    pass

                try:
                    icont_u = ustr(icont)
                except UnicodeError:
                    icont_u = ''

                out = psycopg2.Binary(data)
                cr.execute("UPDATE ir_attachment " \
                            "SET db_datas = %s, file_size=%s, " \
                            " index_content= %s, file_type=%s " \
                            " WHERE id = %s",
                    (out, len(data), icont_u, mime, par.file_id))
            elif self.mode == 'a':
                data = self.getvalue()
                out = psycopg2.Binary(data)
                cr.execute("UPDATE ir_attachment " \
                    "SET db_datas = COALESCE(db_datas,'') || %s, " \
                    "    file_size = COALESCE(file_size, 0) + %s " \
                    " WHERE id = %s",
                    (out, len(data), par.file_id))
            cr.commit()
        except Exception:
            _logger.exception('Cannot update db file #%d for close.', par.file_id)
            raise
        finally:
            cr.close()
        StringIO.close(self)

class document_storage(osv.osv):
    """ The primary object for data storage.
    Each instance of this object is a storage media, in which our application
    can store contents. The object here controls the behaviour of the storage
    media.
    The referring document.directory-ies will control the placement of data
    into the storage.

    It is a bad idea to have multiple document.storage objects pointing to
    the same tree of filesystem storage.
    """
    _name = 'document.storage'
    _description = 'Storage Media'

    _columns = {
        'name': fields.char('Name', size=64, required=True, select=1),
        'write_date': fields.datetime('Date Modified', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True),
        'create_date': fields.datetime('Date Created', readonly=True),
        'create_uid':  fields.many2one('res.users', 'Creator', readonly=True),
        'user_id': fields.many2one('res.users', 'Owner'),
        'group_ids': fields.many2many('res.groups', 'document_storage_group_rel', 'item_id', 'group_id', 'Groups'),
        'dir_ids': fields.one2many('document.directory', 'parent_id', 'Directories'),
        'readonly': fields.boolean('Read Only', help="If set, media is for reading only"),
    }

    _defaults = {
        'user_id': lambda self, cr, uid, ctx: uid,
    }

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
            self._logger.warning("Cannot save data.", exc_info=True)
            # should we really rollback once we have written the actual data?
            # at the db case (only), that rollback would be safe
            raise except_orm(_('Error at doc write!'), str(e))

    def prepare_unlink(self, cr, uid, storage_bo, fil_bo):
        """ Before we unlink a file (fil_boo), prepare the list of real
        files that have to be removed, too. """
        pass

    def do_unlink(self, cr, uid, unres):
        return True

    def simple_rename(self, cr, uid, file_node, new_name, context=None):
        """ A preparation for a file rename.
            It will not affect the database, but merely check and perhaps
            rename the realstore file.

            @return the dict of values that can safely be be stored in the db.
        """
        # nothing to do for a rename, allow to change the db field
        return { 'name': new_name, 'datas_fname': new_name }

    def simple_move(self, cr, uid, file_node, ndir_bro, context=None):
        """ A preparation for a file move.
            It will not affect the database, but merely check and perhaps
            move the realstore file.

            @param ndir_bro a browse object of document.directory, where this
                    file should move to.
            @return the dict of values that can safely be be stored in the db.
        """
        return { 'parent_id': ndir_bro.id }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
