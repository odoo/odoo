# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import hashlib
import itertools
import logging
import mimetypes
import os
import re
from collections import defaultdict
import uuid

from odoo import api, fields, models, tools, _
from odoo.exceptions import AccessError, ValidationError, MissingError, UserError
from odoo.tools import config, human_size, ustr, html_escape
from odoo.tools.mimetypes import guess_mimetype

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    """Attachments are used to link binary files or url to any openerp document.

    External attachment storage
    ---------------------------

    The computed field ``datas`` is implemented using ``_file_read``,
    ``_file_write`` and ``_file_delete``, which can be overridden to implement
    other storage engines. Such methods should check for other location pseudo
    uri (example: hdfs://hadoopserver).

    The default implementation is the file:dirname location that stores files
    on the local filesystem using name based on their sha1 hash
    """
    _name = 'ir.attachment'
    _description = 'Attachment'
    _order = 'id desc'

    def _compute_res_name(self):
        for attachment in self:
            if attachment.res_model and attachment.res_id:
                record = self.env[attachment.res_model].browse(attachment.res_id)
                attachment.res_name = record.display_name
            else:
                attachment.res_name = False

    @api.model
    def _storage(self):
        return self.env['ir.config_parameter'].sudo().get_param('ir_attachment.location', 'file')

    @api.model
    def _filestore(self):
        return config.filestore(self._cr.dbname)

    @api.model
    def force_storage(self):
        """Force all attachments to be stored in the currently configured storage"""
        if not self.env.is_admin():
            raise AccessError(_('Only administrators can execute this action.'))

        # domain to retrieve the attachments to migrate
        domain = {
            'db': [('store_fname', '!=', False)],
            'file': [('db_datas', '!=', False)],
        }[self._storage()]

        for attach in self.search(domain):
            attach.write({'raw': attach.raw, 'mimetype': attach.mimetype})
        return True

    @api.model
    def _full_path(self, path):
        # sanitize path
        path = re.sub('[.]', '', path)
        path = path.strip('/\\')
        return os.path.join(self._filestore(), path)

    @api.model
    def _get_path(self, bin_data, sha):
        # retro compatibility
        fname = sha[:3] + '/' + sha
        full_path = self._full_path(fname)
        if os.path.isfile(full_path):
            return fname, full_path        # keep existing path

        # scatter files across 256 dirs
        # we use '/' in the db (even on windows)
        fname = sha[:2] + '/' + sha
        full_path = self._full_path(fname)
        dirname = os.path.dirname(full_path)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        # prevent sha-1 collision
        if os.path.isfile(full_path) and not self._same_content(bin_data, full_path):
            raise UserError("The attachment is colliding with an existing file.")
        return fname, full_path

    @api.model
    def _file_read(self, fname):
        full_path = self._full_path(fname)
        try:
            with open(full_path, 'rb') as f:
                return f.read()
        except (IOError, OSError):
            _logger.info("_read_file reading %s", full_path, exc_info=True)
        return b''

    @api.model
    def _file_write(self, bin_value, checksum):
        fname, full_path = self._get_path(bin_value, checksum)
        if not os.path.exists(full_path):
            try:
                with open(full_path, 'wb') as fp:
                    fp.write(bin_value)
                # add fname to checklist, in case the transaction aborts
                self._mark_for_gc(fname)
            except IOError:
                _logger.info("_file_write writing %s", full_path, exc_info=True)
        return fname

    @api.model
    def _file_delete(self, fname):
        # simply add fname to checklist, it will be garbage-collected later
        self._mark_for_gc(fname)

    def _mark_for_gc(self, fname):
        """ Add ``fname`` in a checklist for the filestore garbage collection. """
        # we use a spooldir: add an empty file in the subdirectory 'checklist'
        full_path = os.path.join(self._full_path('checklist'), fname)
        if not os.path.exists(full_path):
            dirname = os.path.dirname(full_path)
            if not os.path.isdir(dirname):
                with tools.ignore(OSError):
                    os.makedirs(dirname)
            open(full_path, 'ab').close()

    @api.autovacuum
    def _gc_file_store(self):
        """ Perform the garbage collection of the filestore. """
        if self._storage() != 'file':
            return

        # Continue in a new transaction. The LOCK statement below must be the
        # first one in the current transaction, otherwise the database snapshot
        # used by it may not contain the most recent changes made to the table
        # ir_attachment! Indeed, if concurrent transactions create attachments,
        # the LOCK statement will wait until those concurrent transactions end.
        # But this transaction will not see the new attachements if it has done
        # other requests before the LOCK (like the method _storage() above).
        cr = self._cr
        cr.commit()

        # prevent all concurrent updates on ir_attachment while collecting,
        # but only attempt to grab the lock for a little bit, otherwise it'd
        # start blocking other transactions. (will be retried later anyway)
        cr.execute("SET LOCAL lock_timeout TO '10s'")
        cr.execute("LOCK ir_attachment IN SHARE MODE")

        # retrieve the file names from the checklist
        checklist = {}
        for dirpath, _, filenames in os.walk(self._full_path('checklist')):
            dirname = os.path.basename(dirpath)
            for filename in filenames:
                fname = "%s/%s" % (dirname, filename)
                checklist[fname] = os.path.join(dirpath, filename)

        # determine which files to keep among the checklist
        whitelist = set()
        for names in cr.split_for_in_conditions(checklist):
            cr.execute("SELECT store_fname FROM ir_attachment WHERE store_fname IN %s", [names])
            whitelist.update(row[0] for row in cr.fetchall())

        # remove garbage files, and clean up checklist
        removed = 0
        for fname, filepath in checklist.items():
            if fname not in whitelist:
                try:
                    os.unlink(self._full_path(fname))
                    removed += 1
                except (OSError, IOError):
                    _logger.info("_file_gc could not unlink %s", self._full_path(fname), exc_info=True)
            with tools.ignore(OSError):
                os.unlink(filepath)

        # commit to release the lock
        cr.commit()
        _logger.info("filestore gc %d checked, %d removed", len(checklist), removed)

    @api.depends('store_fname', 'db_datas', 'file_size')
    @api.depends_context('bin_size')
    def _compute_datas(self):
        if self._context.get('bin_size'):
            for attach in self:
                attach.datas = human_size(attach.file_size)
            return

        for attach in self:
            attach.datas = base64.b64encode(attach.raw or b'')

    @api.depends('store_fname', 'db_datas')
    def _compute_raw(self):
        for attach in self:
            if attach.store_fname:
                attach.raw = attach._file_read(attach.store_fname)
            else:
                attach.raw = attach.db_datas

    def _inverse_raw(self):
        self._set_attachment_data(lambda a: a.raw or b'')

    def _inverse_datas(self):
        self._set_attachment_data(lambda attach: base64.b64decode(attach.datas or b''))

    def _set_attachment_data(self, asbytes):
        for attach in self:
            # compute the fields that depend on datas
            bin_data = asbytes(attach)
            vals = self._get_datas_related_values(bin_data, attach.mimetype)

            # take current location in filestore to possibly garbage-collect it
            fname = attach.store_fname
            # write as superuser, as user probably does not have write access
            super(IrAttachment, attach.sudo()).write(vals)
            if fname:
                self._file_delete(fname)

    def _get_datas_related_values(self, data, mimetype):
        values = {
            'file_size': len(data),
            'checksum': self._compute_checksum(data),
            'index_content': self._index(data, mimetype),
            'store_fname': False,
            'db_datas': data,
        }
        if data and self._storage() != 'db':
            values['store_fname'] = self._file_write(data, values['checksum'])
            values['db_datas'] = False
        return values

    def _compute_checksum(self, bin_data):
        """ compute the checksum for the given datas
            :param bin_data : datas in its binary form
        """
        # an empty file has a checksum too (for caching)
        return hashlib.sha1(bin_data or b'').hexdigest()

    @api.model
    def _same_content(self, bin_data, filepath):
        BLOCK_SIZE = 1024
        with open(filepath, 'rb') as fd:
            i = 0
            while True:
                data = fd.read(BLOCK_SIZE)
                if data != bin_data[i * BLOCK_SIZE:(i + 1) * BLOCK_SIZE]:
                    return False
                if not data:
                    break
                i += 1
        return True

    def _compute_mimetype(self, values):
        """ compute the mimetype of the given values
            :param values : dict of values to create or write an ir_attachment
            :return mime : string indicating the mimetype, or application/octet-stream by default
        """
        mimetype = None
        if values.get('mimetype'):
            mimetype = values['mimetype']
        if not mimetype and values.get('name'):
            mimetype = mimetypes.guess_type(values['name'])[0]
        if not mimetype and values.get('url'):
            mimetype = mimetypes.guess_type(values['url'])[0]
        if not mimetype or mimetype == 'application/octet-stream':
            raw = None
            if values.get('raw'):
                raw = values['raw']
            elif values.get('datas'):
                raw = base64.b64decode(values['datas'])
            if raw:
                mimetype = guess_mimetype(raw)
        return mimetype or 'application/octet-stream'

    def _check_contents(self, values):
        mimetype = values['mimetype'] = self._compute_mimetype(values)
        xml_like = 'ht' in mimetype or ( # hta, html, xhtml, etc.
                'xml' in mimetype and    # other xml (svg, text/xml, etc)
                not 'openxmlformats' in mimetype)  # exception for Office formats
        user = self.env.context.get('binary_field_real_user', self.env.user)
        force_text = (xml_like and (not user._is_system() or
            self.env.context.get('attachments_mime_plainxml')))
        if force_text:
            values['mimetype'] = 'text/plain'
        return values

    @api.model
    def _index(self, bin_data, file_type):
        """ compute the index content of the given binary data.
            This is a python implementation of the unix command 'strings'.
            :param bin_data : datas in binary form
            :return index_content : string containing all the printable character of the binary data
        """
        index_content = False
        if file_type:
            index_content = file_type.split('/')[0]
            if index_content == 'text': # compute index_content only for text type
                words = re.findall(b"[\x20-\x7E]{4,}", bin_data)
                index_content = b"\n".join(words).decode('ascii')
        return index_content

    @api.model
    def get_serving_groups(self):
        """ An ir.attachment record may be used as a fallback in the
        http dispatch if its type field is set to "binary" and its url
        field is set as the request's url. Only the groups returned by
        this method are allowed to create and write on such records.
        """
        return ['base.group_system']

    name = fields.Char('Name', required=True)
    description = fields.Text('Description')
    res_name = fields.Char('Resource Name', compute='_compute_res_name')
    res_model = fields.Char('Resource Model', readonly=True, help="The database object this attachment will be attached to.")
    res_field = fields.Char('Resource Field', readonly=True)
    res_id = fields.Many2oneReference('Resource ID', model_field='res_model',
                                      readonly=True, help="The record id this is attached to.")
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
                                 default=lambda self: self.env.company)
    type = fields.Selection([('url', 'URL'), ('binary', 'File')],
                            string='Type', required=True, default='binary', change_default=True,
                            help="You can either upload a file from your computer or copy/paste an internet link to your file.")
    url = fields.Char('Url', index=True, size=1024)
    public = fields.Boolean('Is public document')

    # for external access
    access_token = fields.Char('Access Token', groups="base.group_user")

    # the field 'datas' is computed and may use the other fields below
    raw = fields.Binary(string="File Content (raw)", compute='_compute_raw', inverse='_inverse_raw')
    datas = fields.Binary(string='File Content (base64)', compute='_compute_datas', inverse='_inverse_datas')
    db_datas = fields.Binary('Database Data', attachment=False)
    store_fname = fields.Char('Stored Filename')
    file_size = fields.Integer('File Size', readonly=True)
    checksum = fields.Char("Checksum/SHA1", size=40, index=True, readonly=True)
    mimetype = fields.Char('Mime Type', readonly=True)
    index_content = fields.Text('Indexed Content', readonly=True, prefetch=False)

    def _auto_init(self):
        res = super(IrAttachment, self)._auto_init()
        tools.create_index(self._cr, 'ir_attachment_res_idx',
                           self._table, ['res_model', 'res_id'])
        return res

    @api.constrains('type', 'url')
    def _check_serving_attachments(self):
        if self.env.is_admin():
            return
        for attachment in self:
            # restrict writing on attachments that could be served by the
            # ir.http's dispatch exception handling
            # XDO note: this should be done in check(write), constraints for access rights?
            # XDO note: if read on sudo, read twice, one for constraints, one for _inverse_datas as user
            if attachment.type == 'binary' and attachment.url:
                has_group = self.env.user.has_group
                if not any(has_group(g) for g in attachment.get_serving_groups()):
                    raise ValidationError("Sorry, you are not allowed to write on this document")

    @api.model
    def check(self, mode, values=None):
        """ Restricts the access to an ir.attachment, according to referred mode """
        if self.env.is_superuser():
            return True
        # Always require an internal user (aka, employee) to access to a attachment
        if not (self.env.is_admin() or self.env.user.has_group('base.group_user')):
            raise AccessError(_("Sorry, you are not allowed to access this document."))
        # collect the records to check (by model)
        model_ids = defaultdict(set)            # {model_name: set(ids)}
        if self:
            # DLE P173: `test_01_portal_attachment`
            self.env['ir.attachment'].flush(['res_model', 'res_id', 'create_uid', 'public', 'res_field'])
            self._cr.execute('SELECT res_model, res_id, create_uid, public, res_field FROM ir_attachment WHERE id IN %s', [tuple(self.ids)])
            for res_model, res_id, create_uid, public, res_field in self._cr.fetchall():
                if not self.env.is_system() and res_field:
                    raise AccessError(_("Sorry, you are not allowed to access this document."))
                if public and mode == 'read':
                    continue
                if not (res_model and res_id):
                    continue
                model_ids[res_model].add(res_id)
        if values and values.get('res_model') and values.get('res_id'):
            model_ids[values['res_model']].add(values['res_id'])

        # check access rights on the records
        for res_model, res_ids in model_ids.items():
            # ignore attachments that are not attached to a resource anymore
            # when checking access rights (resource was deleted but attachment
            # was not)
            if res_model not in self.env:
                continue
            if res_model == 'res.users' and len(res_ids) == 1 and self.env.uid == list(res_ids)[0]:
                # by default a user cannot write on itself, despite the list of writeable fields
                # e.g. in the case of a user inserting an image into his image signature
                # we need to bypass this check which would needlessly throw us away
                continue
            records = self.env[res_model].browse(res_ids).exists()
            # For related models, check if we can write to the model, as unlinking
            # and creating attachments can be seen as an update to the model
            access_mode = 'write' if mode in ('create', 'unlink') else mode
            records.check_access_rights(access_mode)
            records.check_access_rule(access_mode)


    def _read_group_allowed_fields(self):
        return ['type', 'company_id', 'res_id', 'create_date', 'create_uid', 'name', 'mimetype', 'id', 'url', 'res_field', 'res_model']

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Override read_group to add res_field=False in domain if not present."""
        if not fields:
            raise AccessError(_("Sorry, you must provide fields to read on attachments"))
        if any('(' in field for field in fields + groupby):
            raise AccessError(_("Sorry, the syntax 'name:agg(field)' is not available for attachments"))
        if not any(item[0] in ('id', 'res_field') for item in domain):
            domain.insert(0, ('res_field', '=', False))
        groupby = [groupby] if isinstance(groupby, str) else groupby
        allowed_fields = self._read_group_allowed_fields()
        fields_set = set(field.split(':')[0] for field in fields + groupby)
        if not self.env.is_system() and (not fields or fields_set.difference(allowed_fields)):
            raise AccessError(_("Sorry, you are not allowed to access these fields on attachments."))
        return super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        # add res_field=False in domain if not present; the arg[0] trick below
        # works for domain items and '&'/'|'/'!' operators too
        discard_binary_fields_attachments = False
        if not any(arg[0] in ('id', 'res_field') for arg in args):
            discard_binary_fields_attachments = True
            args.insert(0, ('res_field', '=', False))

        ids = super(IrAttachment, self)._search(args, offset=offset, limit=limit, order=order,
                                                count=False, access_rights_uid=access_rights_uid)

        if self.env.is_superuser():
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
        model_attachments = defaultdict(lambda: defaultdict(set))   # {res_model: {res_id: set(ids)}}
        binary_fields_attachments = set()
        self._cr.execute("""SELECT id, res_model, res_id, public, res_field FROM ir_attachment WHERE id IN %s""", [tuple(ids)])
        for row in self._cr.dictfetchall():
            if not row['res_model'] or row['public']:
                continue
            # model_attachments = {res_model: {res_id: set(ids)}}
            model_attachments[row['res_model']][row['res_id']].add(row['id'])
            # Should not retrieve binary fields attachments if not explicitly required
            if discard_binary_fields_attachments and row['res_field']:
                binary_fields_attachments.add(row['id'])

        if binary_fields_attachments:
            ids.difference_update(binary_fields_attachments)

        # To avoid multiple queries for each attachment found, checks are
        # performed in batch as much as possible.
        for res_model, targets in model_attachments.items():
            if res_model not in self.env:
                continue
            if not self.env[res_model].check_access_rights('read', False):
                # remove all corresponding attachment ids
                ids.difference_update(itertools.chain(*targets.values()))
                continue
            # filter ids according to what access rules permit
            target_ids = list(targets)
            allowed = self.env[res_model].with_context(active_test=False).search([('id', 'in', target_ids)])
            for res_id in set(target_ids).difference(allowed.ids):
                ids.difference_update(targets[res_id])

        # sort result according to the original sort ordering
        result = [id for id in orig_ids if id in ids]

        # If the original search reached the limit, it is important the
        # filtered record set does so too. When a JS view receive a
        # record set whose length is below the limit, it thinks it
        # reached the last page. To avoid an infinite recursion due to the
        # permission checks the sub-call need to be aware of the number of
        # expected records to retrieve
        if len(orig_ids) == limit and len(result) < self._context.get('need', limit):
            need = self._context.get('need', limit) - len(result)
            result.extend(self.with_context(need=need)._search(args, offset=offset + len(orig_ids),
                                       limit=limit, order=order, count=count,
                                       access_rights_uid=access_rights_uid)[:limit - len(result)])

        return len(result) if count else list(result)

    def _read(self, fields):
        self.check('read')
        return super(IrAttachment, self)._read(fields)

    def write(self, vals):
        self.check('write', values=vals)
        # remove computed field depending of datas
        for field in ('file_size', 'checksum'):
            vals.pop(field, False)
        if 'mimetype' in vals or 'datas' in vals:
            vals = self._check_contents(vals)
        return super(IrAttachment, self).write(vals)

    def copy(self, default=None):
        self.check('write')
        return super(IrAttachment, self).copy(default)

    def unlink(self):
        if not self:
            return True
        self.check('unlink')

        # First delete in the database, *then* in the filesystem if the
        # database allowed it. Helps avoid errors when concurrent transactions
        # are deleting the same file, and some of the transactions are
        # rolled back by PostgreSQL (due to concurrent updates detection).
        to_delete = set(attach.store_fname for attach in self if attach.store_fname)
        res = super(IrAttachment, self).unlink()
        for file_path in to_delete:
            self._file_delete(file_path)

        return res

    @api.model_create_multi
    def create(self, vals_list):
        record_tuple_set = set()
        for values in vals_list:
            # remove computed field depending of datas
            for field in ('file_size', 'checksum'):
                values.pop(field, False)
            values = self._check_contents(values)
            if 'datas' in values:
                data = values.pop('datas')
                values.update(self._get_datas_related_values(base64.b64decode(data or b''), values['mimetype']))
            # 'check()' only uses res_model and res_id from values, and make an exists.
            # We can group the values by model, res_id to make only one query when 
            # creating multiple attachments on a single record.
            record_tuple = (values.get('res_model'), values.get('res_id'))
            record_tuple_set.add(record_tuple)
        for record_tuple in record_tuple_set:
            (res_model, res_id) = record_tuple
            self.check('create', values={'res_model':res_model, 'res_id':res_id})
        return super(IrAttachment, self).create(vals_list)

    def _post_add_create(self):
        pass

    def generate_access_token(self):
        tokens = []
        for attachment in self:
            if attachment.access_token:
                tokens.append(attachment.access_token)
                continue
            access_token = self._generate_access_token()
            attachment.write({'access_token': access_token})
            tokens.append(access_token)
        return tokens

    def _generate_access_token(self):
        return str(uuid.uuid4())

    @api.model
    def action_get(self):
        return self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')

    @api.model
    def get_serve_attachment(self, url, extra_domain=None, extra_fields=None, order=None):
        domain = [('type', '=', 'binary'), ('url', '=', url)] + (extra_domain or [])
        fieldNames = ['__last_update', 'datas', 'mimetype'] + (extra_fields or [])
        return self.search_read(domain, fieldNames, order=order, limit=1)
