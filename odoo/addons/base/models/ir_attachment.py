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
from odoo.exceptions import AccessError, ValidationError, MissingError
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

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for attachment in self:
            if attachment.res_model and attachment.res_id:
                record = self.env[attachment.res_model].browse(attachment.res_id)
                attachment.res_name = record.display_name

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
            attach.write({'datas': attach.datas})
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
        return fname, full_path

    @api.model
    def _file_read(self, fname, bin_size=False):
        full_path = self._full_path(fname)
        r = ''
        try:
            if bin_size:
                r = human_size(os.path.getsize(full_path))
            else:
                r = base64.b64encode(open(full_path,'rb').read())
        except (IOError, OSError):
            _logger.info("_read_file reading %s", full_path, exc_info=True)
        return r

    @api.model
    def _file_write(self, value, checksum):
        bin_value = base64.b64decode(value)
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

    @api.model
    def _file_gc(self):
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

        # prevent all concurrent updates on ir_attachment while collecting!
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

    @api.depends('store_fname', 'db_datas')
    def _compute_datas(self):
        bin_size = self._context.get('bin_size')
        for attach in self:
            if attach.store_fname:
                attach.datas = self._file_read(attach.store_fname, bin_size)
            else:
                attach.datas = attach.db_datas

    def _inverse_datas(self):
        location = self._storage()
        for attach in self:
            # compute the fields that depend on datas
            value = attach.datas
            bin_data = base64.b64decode(value) if value else b''
            vals = {
                'file_size': len(bin_data),
                'checksum': self._compute_checksum(bin_data),
                'index_content': self._index(bin_data, attach.mimetype),
                'store_fname': False,
                'db_datas': value,
            }
            if value and location != 'db':
                # save it to the filestore
                vals['store_fname'] = self._file_write(value, vals['checksum'])
                vals['db_datas'] = False

            # take current location in filestore to possibly garbage-collect it
            fname = attach.store_fname
            # write as superuser, as user probably does not have write access
            super(IrAttachment, attach.sudo()).write(vals)
            if fname:
                self._file_delete(fname)

    def _compute_checksum(self, bin_data):
        """ compute the checksum for the given datas
            :param bin_data : datas in its binary form
        """
        # an empty file has a checksum too (for caching)
        return hashlib.sha1(bin_data or b'').hexdigest()

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
        if values.get('datas') and (not mimetype or mimetype == 'application/octet-stream'):
            mimetype = guess_mimetype(base64.b64decode(values['datas']))
        return mimetype or 'application/octet-stream'

    def _check_contents(self, values):
        mimetype = values['mimetype'] = self._compute_mimetype(values)
        xml_like = 'ht' in mimetype or 'xml' in mimetype # hta, html, xhtml, etc.
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
    res_name = fields.Char('Resource Name', compute='_compute_res_name', store=True)
    res_model = fields.Char('Resource Model', readonly=True, help="The database object this attachment will be attached to.")
    res_field = fields.Char('Resource Field', readonly=True)
    res_id = fields.Integer('Resource ID', readonly=True, help="The record id this is attached to.")
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
    datas = fields.Binary(string='File Content', compute='_compute_datas', inverse='_inverse_datas')
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
                if not any([has_group(g) for g in attachment.get_serving_groups()]):
                    raise ValidationError("Sorry, you are not allowed to write on this document")

    @api.model
    def check(self, mode, values=None):
        """Restricts the access to an ir.attachment, according to referred model
        In the 'document' module, it is overriden to relax this hard rule, since
        more complex ones apply there.
        """
        if self.env.is_superuser():
            return True
        # collect the records to check (by model)
        model_ids = defaultdict(set)            # {model_name: set(ids)}
        require_employee = False
        if self:
            self._cr.execute('SELECT res_model, res_id, create_uid, public, res_field FROM ir_attachment WHERE id IN %s', [tuple(self.ids)])
            for res_model, res_id, create_uid, public, res_field in self._cr.fetchall():
                if not self.env.is_system() and res_field:
                    raise AccessError(_("Sorry, you are not allowed to access this document."))
                if public and mode == 'read':
                    continue
                if not (res_model and res_id):
                    if create_uid != self._uid:
                        require_employee = True
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
                require_employee = True
                continue
            elif res_model == 'res.users' and len(res_ids) == 1 and self._uid == list(res_ids)[0]:
                # by default a user cannot write on itself, despite the list of writeable fields
                # e.g. in the case of a user inserting an image into his image signature
                # we need to bypass this check which would needlessly throw us away
                continue
            records = self.env[res_model].browse(res_ids).exists()
            if len(records) < len(res_ids):
                require_employee = True
            # For related models, check if we can write to the model, as unlinking
            # and creating attachments can be seen as an update to the model
            records.check_access_rights('write' if mode in ('create', 'unlink') else mode)
            records.check_access_rule(mode)

        if require_employee:
            if not (self.env.is_admin() or self.env.user.has_group('base.group_user')):
                raise AccessError(_("Sorry, you are not allowed to access this document."))

    def _read_group_allowed_fields(self):
        return ['type', 'company_id', 'res_id', 'create_date', 'create_uid', 'res_name', 'name', 'mimetype', 'id', 'url', 'res_field', 'res_model']

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
        if not any(arg[0] in ('id', 'res_field') for arg in args):
            args.insert(0, ('res_field', '=', False))

        ids = super(IrAttachment, self)._search(args, offset=offset, limit=limit, order=order,
                                                count=False, access_rights_uid=access_rights_uid)

        if self.env.is_system():
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
            # Should not retrieve binary fields attachments
            if row['res_field']:
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
        return len(result) if count else list(result)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        self.check('read')
        return super(IrAttachment, self).read(fields, load=load)

    @api.multi
    def write(self, vals):
        self.check('write', values=vals)
        # remove computed field depending of datas
        for field in ('file_size', 'checksum'):
            vals.pop(field, False)
        if 'mimetype' in vals or 'datas' in vals:
            vals = self._check_contents(vals)
        return super(IrAttachment, self).write(vals)

    @api.multi
    def copy(self, default=None):
        self.check('write')
        return super(IrAttachment, self).copy(default)

    @api.multi
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
            # 'check()' only uses res_model and res_id from values, and make an exists.
            # We can group the values by model, res_id to make only one query when 
            # creating multiple attachments on a single record.
            record_tuple = (values.get('res_model'), values.get('res_id'))
            record_tuple_set.add(record_tuple)
        for record_tuple in record_tuple_set:
            (res_model, res_id) = record_tuple
            self.check('write', values={'res_model':res_model, 'res_id':res_id})
        return super(IrAttachment, self).create(vals_list)

    @api.multi
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
        return self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')

    @api.model
    def get_serve_attachment(self, url, extra_domain=None, extra_fields=None, order=None):
        domain = [('type', '=', 'binary'), ('url', '=', url)] + (extra_domain or [])
        fieldNames = ['__last_update', 'datas', 'mimetype'] + (extra_fields or [])
        return self.search_read(domain, fieldNames, order=order, limit=1)

    @api.model
    def get_attachment_by_key(self, key, extra_domain=None, order=None):
        domain = [('key', '=', key)] + (extra_domain or [])
        return self.search(domain, order=order, limit=1)
