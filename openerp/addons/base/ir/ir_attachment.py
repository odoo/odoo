# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import itertools
import logging
import mimetypes
import os
import re

from openerp import tools
from openerp.tools.translate import _
from openerp.exceptions import AccessError
from openerp.osv import fields,osv
from openerp import SUPERUSER_ID
from openerp.exceptions import UserError
from openerp.tools.translate import _
from openerp.tools.misc import ustr

_logger = logging.getLogger(__name__)

try:
    import magic
except ImportError:
    magic = None

# We define our own guess_mimetype implementation and if magic is available we
# use it instead.

# However there are 2 python libs named 'magic' with incompatible api.
# magic from pypi https://pypi.python.org/pypi/python-magic/
# magic from file(1) https://packages.debian.org/squeeze/python-magic

def guess_mimetype(bin_data):
    # by default, guess the type using the magic number of file hex signature (like magic, but more limited)
    # see http://www.filesignatures.net/ for file signatures
    mapping = (
        # pdf
        ('application/pdf', ['%PDF']),
        # jpg, jpeg, png, gif
        ('image/jpeg', ['\xFF\xD8\xFF\xE0', '\xFF\xD8\xFF\xE2', '\xFF\xD8\xFF\xE3', '\xFF\xD8\xFF\xE1']),
        ('image/png', ['\x89\x50\x4E\x47\x0D\x0A\x1A\x0A']),
        ('image/gif', ['GIF87a', '\x47\x49\x46\x38\x37\x61', 'GIF89a', '\x47\x49\x46\x38\x39\x61']),
        # docx, odt, doc, xls
        ('application/msword', ['PK\x03\x04', '\xCF\x11\xE0\xA1\xB1\x1A\xE1\x00', '\xEC\xA5\xC1\x00', '\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1', '\x0D\x44\x4F\x43']),
        # zip, but will include jar, odt, ods, odp, docx, xlsx, pptx, apk
        ('application/zip', ['PK']),
        ('application/vnd.ms-excel', ['\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1', '\x09\x08\x10\x00\x00\x06\x05\x00', '\xFD\xFF\xFF\xFF\x10', '\xFD\xFF\xFF\xFF\x1F', '\xFD\xFF\xFF\xFF\x23', '\xFD\xFF\xFF\xFF\x28', '\xFD\xFF\xFF\xFF\x29']),
    )
    for mimetype, signatures in mapping:
        for signature in signatures:
            if bin_data.startswith(signature):
                return mimetype
    return 'application/octet-stream'

# if available adapt magic from pypi
if hasattr(magic,'from_buffer'):
    guess_mimetype = lambda bin_data: magic.from_buffer(bin_data, mime=True)
# or if available adapt magic from file(1)
elif hasattr(magic,'open'):
    ms = magic.open(magic.MAGIC_MIME_TYPE)
    ms.load()
    guess_mimetype = ms.buffer


class ir_attachment(osv.osv):
    """Attachments are used to link binary files or url to any openerp document.

    External attachment storage
    ---------------------------

    The 'data' function field (_data_get,data_set) is implemented using
    _file_read, _file_write and _file_delete which can be overridden to
    implement other storage engines, such methods should check for other
    location pseudo uri (example: hdfs://hadoppserver)

    The default implementation is the file:dirname location that stores files
    on the local filesystem using name based on their sha1 hash
    """
    _order = 'id desc'
    def _name_get_resname(self, cr, uid, ids, object, method, context):
        data = {}
        for attachment in self.browse(cr, uid, ids, context=context):
            model_object = attachment.res_model
            res_id = attachment.res_id
            if model_object and res_id:
                model_pool = self.pool[model_object]
                res = model_pool.name_get(cr,uid,[res_id],context)
                res_name = res and res[0][1] or None
                if res_name:
                    field = self._columns.get('res_name',False)
                    if field and len(res_name) > field.size:
                        res_name = res_name[:30] + '...'
                data[attachment.id] = res_name or False
            else:
                data[attachment.id] = False
        return data

    def _storage(self, cr, uid, context=None):
        return self.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'ir_attachment.location', 'file')

    def _filestore(self, cr, uid, context=None):
        return tools.config.filestore(cr.dbname)

    def force_storage(self, cr, uid, context=None):
        """Force all attachments to be stored in the currently configured storage"""
        if not self.pool['res.users']._is_admin(cr, uid, [uid]):
            raise AccessError(_('Only administrators can execute this action.'))

        location = self._storage(cr, uid, context)
        domain = {
            'db': [('store_fname', '!=', False)],
            'file': [('db_datas', '!=', False)],
        }[location]

        ids = self.search(cr, uid, domain, context=context)
        for attach in self.browse(cr, uid, ids, context=context):
            attach.write({'datas': attach.datas})
        return True

    # 'data' field implementation
    def _full_path(self, cr, uid, path):
        # sanitize ath
        path = re.sub('[.]', '', path)
        path = path.strip('/\\')
        return os.path.join(self._filestore(cr, uid), path)

    def _get_path(self, cr, uid, bin_data, sha):
        # retro compatibility
        fname = sha[:3] + '/' + sha
        full_path = self._full_path(cr, uid, fname)
        if os.path.isfile(full_path):
            return fname, full_path        # keep existing path

        # scatter files across 256 dirs
        # we use '/' in the db (even on windows)
        fname = sha[:2] + '/' + sha
        full_path = self._full_path(cr, uid, fname)
        dirname = os.path.dirname(full_path)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        return fname, full_path

    def _file_read(self, cr, uid, fname, bin_size=False):
        full_path = self._full_path(cr, uid, fname)
        r = ''
        try:
            if bin_size:
                r = os.path.getsize(full_path)
            else:
                r = open(full_path,'rb').read().encode('base64')
        except (IOError, OSError):
            _logger.info("_read_file reading %s", full_path, exc_info=True)
        return r

    def _file_write(self, cr, uid, value, checksum):
        bin_value = value.decode('base64')
        fname, full_path = self._get_path(cr, uid, bin_value, checksum)
        if not os.path.exists(full_path):
            try:
                with open(full_path, 'wb') as fp:
                    fp.write(bin_value)
            except IOError:
                _logger.info("_file_write writing %s", full_path, exc_info=True)
        return fname

    def _file_delete(self, cr, uid, fname):
        # using SQL to include files hidden through unlink or due to record rules
        cr.execute("SELECT COUNT(*) FROM ir_attachment WHERE store_fname = %s", (fname,))
        count = cr.fetchone()[0]
        full_path = self._full_path(cr, uid, fname)
        if not count and os.path.exists(full_path):
            try:
                os.unlink(full_path)
            except OSError:
                _logger.info("_file_delete could not unlink %s", full_path, exc_info=True)
            except IOError:
                # Harmless and needed for race conditions
                _logger.info("_file_delete could not unlink %s", full_path, exc_info=True)

    def _data_get(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        result = {}
        bin_size = context.get('bin_size')
        for attach in self.browse(cr, uid, ids, context=context):
            if attach.store_fname:
                result[attach.id] = self._file_read(cr, uid, attach.store_fname, bin_size)
            else:
                result[attach.id] = attach.db_datas
        return result

    def _data_set(self, cr, uid, id, name, value, arg, context=None):
        # compute the field depending of datas, supporting the case of a empty/None datas
        bin_data = value and value.decode('base64') or '' # empty string to compute its hash
        checksum = self._compute_checksum(bin_data)
        vals = {
            'file_size': len(bin_data),
            'checksum' : checksum,
        }
        # We dont handle setting data to null
        # datas is false, but file_size and checksum are not (computed as datas is an empty string)
        if not value:
            # reset computed fields
            super(ir_attachment, self).write(cr, SUPERUSER_ID, [id], vals, context=context)
            return True
        if context is None:
            context = {}
        # browse the attachment and get the file to delete
        attach = self.browse(cr, uid, id, context=context)
        fname_to_delete = attach.store_fname
        location = self._storage(cr, uid, context)
        # compute the index_content field
        vals['index_content'] = self._index(cr, SUPERUSER_ID, bin_data, attach.datas_fname, attach.mimetype),
        if location != 'db':
            # create the file
            fname = self._file_write(cr, uid, value, checksum)
            vals.update({
                'store_fname': fname,
                'db_datas': False
            })
        else:
            vals.update({
                'store_fname': False,
                'db_datas': value
            })
        # SUPERUSER_ID as probably don't have write access, trigger during create
        super(ir_attachment, self).write(cr, SUPERUSER_ID, [id], vals, context=context)

        # After de-referencing the file in the database, check whether we need
        # to garbage-collect it on the filesystem
        if fname_to_delete:
            self._file_delete(cr, uid, fname_to_delete)
        return True

    def _compute_checksum(self, bin_data):
        """ compute the checksum for the given datas
            :param bin_data : datas in its binary form
        """
        # an empty file has a checksum too (for caching)
        return hashlib.sha1(bin_data or '').hexdigest()

    def _compute_mimetype(self, values):
        """ compute the mimetype of the given values
            :param values : dict of values to create or write an ir_attachment
            :return mime : string indicating the mimetype, or application/octet-stream by default
        """
        mimetype = 'application/octet-stream'
        if values.get('datas_fname'):
            mimetype = mimetypes.guess_type(values['datas_fname'])[0]
        if values.get('url'):
            mimetype = mimetypes.guess_type(values['url'])[0]
        if values.get('datas') and (not mimetype or mimetype == 'application/octet-stream'):
            mimetype = guess_mimetype(values['datas'].decode('base64'))
        return mimetype

    def _index(self, cr, uid, bin_data, datas_fname, file_type):
        """ compute the index content of the given filename, or binary data.
            This is a python implementation of the unix command 'strings'.
            :param bin_data : datas in binary form
            :return index_content : string containing all the printable character of the binary data
        """
        index_content = False
        if file_type:
            index_content = file_type.split('/')[0]
            if index_content == 'text': # compute index_content only for text type
                words = re.findall("[^\x00-\x1F\x7F-\xFF]{4,}", bin_data)
                index_content = ustr("\n".join(words))
        return index_content


    _name = 'ir.attachment'
    _columns = {
        'name': fields.char('Attachment Name', required=True),
        'datas_fname': fields.char('File Name'),
        'description': fields.text('Description'),
        'res_name': fields.function(_name_get_resname, type='char', string='Resource Name', store=True),
        'res_model': fields.char('Resource Model', readonly=True, help="The database object this attachment will be attached to"),
        'res_field': fields.char('Resource Field', readonly=True),
        'res_id': fields.integer('Resource ID', readonly=True, help="The record id this is attached to"),
        'create_date': fields.datetime('Date Created', readonly=True),
        'create_uid':  fields.many2one('res.users', 'Owner', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', change_default=True),
        'type': fields.selection( [ ('url','URL'), ('binary','File'), ],
                'Type', help="You can either upload a file from your computer or copy/paste an internet link to your file", required=True, change_default=True),
        'url': fields.char('Url', size=1024),
        # al: We keep shitty field names for backward compatibility with document
        'datas': fields.function(_data_get, fnct_inv=_data_set, string='File Content', type="binary", nodrop=True),
        'store_fname': fields.char('Stored Filename'),
        'db_datas': fields.binary('Database Data'),
        # computed fields depending on datas
        'file_size': fields.integer('File Size', readonly=True),
        'checksum': fields.char("Checksum/SHA1", size=40, select=True, readonly=True),
        'mimetype': fields.char('Mime Type', readonly=True),
        'index_content': fields.text('Indexed Content', readonly=True),
        'public': fields.boolean('Is public document'),
    }

    _defaults = {
        'type': 'binary',
        'file_size': 0,
        'mimetype' : False,
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'ir.attachment', context=c),
    }

    def _auto_init(self, cr, context=None):
        super(ir_attachment, self)._auto_init(cr, context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('ir_attachment_res_idx',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX ir_attachment_res_idx ON ir_attachment (res_model, res_id)')
            cr.commit()

    def check(self, cr, uid, ids, mode, context=None, values=None):
        """Restricts the access to an ir.attachment, according to referred model
        In the 'document' module, it is overriden to relax this hard rule, since
        more complex ones apply there.
        """
        res_ids = {}
        require_employee = False
        if ids:
            if isinstance(ids, (int, long)):
                ids = [ids]
            cr.execute('SELECT res_model, res_id, create_uid, public FROM ir_attachment WHERE id = ANY (%s)', (ids,))
            for rmod, rid, create_uid, public in cr.fetchall():
                if public and mode == 'read':
                    continue
                if not (rmod and rid):
                    if create_uid != uid:
                        require_employee = True
                    continue
                res_ids.setdefault(rmod,set()).add(rid)
        if values:
            if values.get('res_model') and values.get('res_id'):
                res_ids.setdefault(values['res_model'],set()).add(values['res_id'])

        ima = self.pool.get('ir.model.access')
        for model, mids in res_ids.items():
            # ignore attachments that are not attached to a resource anymore when checking access rights
            # (resource was deleted but attachment was not)
            if not self.pool.get(model):
                require_employee = True
                continue
            existing_ids = self.pool[model].exists(cr, uid, mids)
            if len(existing_ids) != len(mids):
                require_employee = True
            # For related models, check if we can write to the model, as unlinking
            # and creating attachments can be seen as an update to the model
            if (mode in ['unlink','create']):
                ima.check(cr, uid, model, 'write')
            else:
                ima.check(cr, uid, model, mode)
            self.pool[model].check_access_rule(cr, uid, existing_ids, mode, context=context)
        if require_employee:
            if not uid == SUPERUSER_ID and not self.pool['res.users'].has_group(cr, uid, 'base.group_user'):
                raise AccessError(_("Sorry, you are not allowed to access this document."))

    def _search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False, access_rights_uid=None):
        # add res_field=False in domain if not present; the arg[0] trick below
        # works for domain items and '&'/'|'/'!' operators too
        if not any(arg[0] in ('id', 'res_field') for arg in args):
            args.insert(0, ('res_field', '=', False))

        ids = super(ir_attachment, self)._search(cr, uid, args, offset=offset,
                                                 limit=limit, order=order,
                                                 context=context, count=False,
                                                 access_rights_uid=access_rights_uid)

        if uid == SUPERUSER_ID:
            # rules do not apply for the superuser
            return len(ids) if count else ids

        if not ids:
            return 0 if count else []

        # Work with a set, as list.remove() is prohibitive for large lists of documents
        # (takes 20+ seconds on a db with 100k docs during search_count()!)
        orig_ids = ids
        ids = set(ids)

        # For attachments, the permissions of the document they are attached to
        # apply, so we must remove attachments for which the user cannot access
        # the linked document.
        # Use pure SQL rather than read() as it is about 50% faster for large dbs (100k+ docs),
        # and the permissions are checked in super() and below anyway.
        cr.execute("""SELECT id, res_model, res_id, public FROM ir_attachment WHERE id = ANY(%s)""", (list(ids),))
        targets = cr.dictfetchall()
        model_attachments = {}
        for target_dict in targets:
            if not target_dict['res_model'] or target_dict['public']:
                continue
            # model_attachments = { 'model': { 'res_id': [id1,id2] } }
            model_attachments.setdefault(target_dict['res_model'],{}).setdefault(target_dict['res_id'] or 0, set()).add(target_dict['id'])

        # To avoid multiple queries for each attachment found, checks are
        # performed in batch as much as possible.
        ima = self.pool.get('ir.model.access')
        for model, targets in model_attachments.iteritems():
            if model not in self.pool:
                continue
            if not ima.check(cr, uid, model, 'read', False):
                # remove all corresponding attachment ids
                for attach_id in itertools.chain(*targets.values()):
                    ids.remove(attach_id)
                continue # skip ir.rule processing, these ones are out already

            # filter ids according to what access rules permit
            target_ids = targets.keys()
            allowed_ids = [0] + self.pool[model].search(cr, uid, [('id', 'in', target_ids)], context=context)
            disallowed_ids = set(target_ids).difference(allowed_ids)
            for res_id in disallowed_ids:
                for attach_id in targets[res_id]:
                    ids.remove(attach_id)

        # sort result according to the original sort ordering
        result = [id for id in orig_ids if id in ids]
        return len(result) if count else list(result)

    def read(self, cr, uid, ids, fields_to_read=None, context=None, load='_classic_read'):
        if isinstance(ids, (int, long)):
            ids = [ids]
        self.check(cr, uid, ids, 'read', context=context)
        return super(ir_attachment, self).read(cr, uid, ids, fields_to_read, context=context, load=load)

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        self.check(cr, uid, ids, 'write', context=context, values=vals)
        # remove computed field depending of datas
        for field in ['file_size', 'checksum']:
            vals.pop(field, False)
        return super(ir_attachment, self).write(cr, uid, ids, vals, context)

    def copy(self, cr, uid, id, default=None, context=None):
        self.check(cr, uid, [id], 'write', context=context)
        return super(ir_attachment, self).copy(cr, uid, id, default, context)

    def unlink(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        self.check(cr, uid, ids, 'unlink', context=context)

        # First delete in the database, *then* in the filesystem if the
        # database allowed it. Helps avoid errors when concurrent transactions
        # are deleting the same file, and some of the transactions are
        # rolled back by PostgreSQL (due to concurrent updates detection).
        to_delete = [a.store_fname
                        for a in self.browse(cr, uid, ids, context=context)
                            if a.store_fname]
        res = super(ir_attachment, self).unlink(cr, uid, ids, context)
        for file_path in to_delete:
            self._file_delete(cr, uid, file_path)

        return res

    def create(self, cr, uid, values, context=None):
        # remove computed field depending of datas
        for field in ['file_size', 'checksum']:
            values.pop(field, False)
        # if mimetype not given, compute it !
        if 'mimetype' not in values:
            values['mimetype'] = self._compute_mimetype(values)
        self.check(cr, uid, [], mode='write', context=context, values=values)
        return super(ir_attachment, self).create(cr, uid, values, context)

    def action_get(self, cr, uid, context=None):
        return self.pool.get('ir.actions.act_window').for_xml_id(
            cr, uid, 'base', 'action_attachment', context=context)
