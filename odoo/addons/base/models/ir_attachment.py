# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import annotations

import contextlib
import hashlib
import io
import logging
import mimetypes
import os
import re
import shutil
import stat
import tempfile
import typing
import uuid
import warnings
from collections import defaultdict
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.fields import Domain
from odoo.http.stream import Stream
from odoo.tools import (
    OrderedSet,
    SQL,
    config,
    consteq,
    image,
    split_every,
    str2bool,
)
from odoo.tools.binary import EMPTY_BINARY, BinaryBytes, BinaryValue
from odoo.tools.constants import PREFETCH_MAX
from odoo.tools.mimetypes import guess_file_mimetype, guess_mimetype
from odoo.tools.misc import limited_field_access_token

if typing.TYPE_CHECKING:
    from collections.abc import Collection

_logger = logging.getLogger(__name__)
SECURITY_FIELDS = ('res_model', 'res_id', 'create_uid', 'public', 'res_field')
MAX_COMODELS_FOR_DOMAIN = 5
MAX_SEARCH_LIMIT = PREFETCH_MAX * 10
CREATE_FROM_STREAM_FLAG = object()  # sentinel that cannot be given over RPC
WRITE_FILE_SUFFIX = '.__new'
GC_FILE_SUFFIX = '.__gc'
GC_GRACE_PERIOD = 1800  # 30 minutes
GC_GRACE_PERIOD_MAX = 604800  # 1 week


def condition_values(model, field_name, domain):
    """Get the values in the domain for a specific field name.

    Returns the values appearing in the `in` conditions that would be restricted
    to by the domain.
    """
    domain = domain.optimize(model)
    for condition in domain.map_conditions(
        lambda cond: cond
        if cond.field_expr == field_name and cond.operator == 'in'
        else Domain.TRUE
    ).optimize(model).iter_conditions():
        return condition.value
    return None


class IrAttachment(models.Model):
    """Attachments are used to link binary files or url to any openerp document.

    External attachment storage
    ---------------------------

    The computed field ``raw`` is implemented using ``_file_read``,
    ``_file_write`` and ``_file_delete``, which can be overridden to implement
    other storage engines. Such methods should check for other location pseudo
    uri (example: hdfs://hadoopserver).

    The default implementation is the file:dirname location that stores files
    on the local filesystem using name based on their sha1 hash
    """
    _name = 'ir.attachment'
    _description = 'Attachment'
    _order = 'id desc'
    _access_domain_heavy = True

    def _compute_res_name(self):
        for attachment in self:
            if attachment.res_model and attachment.res_id:
                record = self.env[attachment.res_model].browse(attachment.res_id)
                attachment.res_name = record.display_name
            else:
                attachment.res_name = False

    @api.model
    def _storage(self):
        return self.env['ir.config_parameter'].sudo().get_str('ir_attachment.location') or 'file'

    @api.model
    def _filestore(self):
        return config.filestore(self.env.cr.dbname)

    @api.model
    def _get_storage_domain(self):
        # domain to retrieve the attachments to migrate
        return {
            'db': [('store_fname', '!=', False)],
            'file': [('db_datas', '!=', False)],
        }[self._storage()]

    @api.model
    def force_storage(self):
        """Force all attachments to be stored in the currently configured storage"""
        if not self.env.is_admin():
            raise AccessError(_('Only administrators can execute this action.'))

        # Migrate only binary attachments and bypass the res_field automatic
        # filter added in _search override
        self.search(Domain.AND([
            self._get_storage_domain(),
            ['&', ('type', '=', 'binary'), '|', ('res_field', '=', False), ('res_field', '!=', False)]
        ]))._migrate()

    def _migrate(self):
        record_count = len(self)
        storage = self._storage().upper()
        for index, attach in enumerate(self):
            _logger.debug("Migrate attachment %s/%s to %s", index + 1, record_count, storage)
            # pass mimetype, to avoid recomputation
            attach.write({'raw': attach.raw, 'mimetype': attach.mimetype})

    @api.model
    def _full_path(self, fname):
        assert not fname.endswith(GC_FILE_SUFFIX)
        # sanitize path
        fname = re.sub(r'[.:]', '', fname).strip('/\\')
        return os.path.join(self._filestore(), fname)

    @api.model
    def _file_fname(self, sha: str) -> str:
        # scatter files across 256 dirs
        # we use '/' in the db (even on windows)
        return sha[:2] + '/' + sha

    @api.model
    def _file_read(self, fname: str) -> BinaryValue:
        assert isinstance(self, IrAttachment)
        try:
            return LocalBinaryFile(fname, self)
        except OSError:
            full_path = self._full_path(fname)
            _logger.info("_file_read reading %s", full_path, exc_info=True)
            return EMPTY_BINARY

    @api.model
    def _file_write(self, fname: str, bin_value: io.IOBase) -> None:
        """ Persist the data for the given fname. """
        assert isinstance(self, IrAttachment)
        assert hasattr(bin_value, 'read') and hasattr(bin_value, 'seek'), f'expecting a seekable IO object, got {bin_value}'
        full_path = self._full_path(fname)
        try:
            # check if file exists and prevent sha-1 collision
            try:
                with open(full_path, 'rb') as existing_file:
                    if self._same_content(bin_value, existing_file):
                        return
                    raise RuntimeError(f"The attachment {fname} collides with an existing file.")
            except FileNotFoundError:
                pass
            # make sure the directory exists
            dirname = os.path.dirname(full_path)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            # add fname to checklist, in case the transaction aborts
            self._mark_for_gc(fname)
            # write and set permissions
            full_path_tmp = full_path + WRITE_FILE_SUFFIX
            with open(full_path_tmp, 'wb') as fp:
                shutil.copyfileobj(bin_value, fp)
            # Prevent changing the content of the file, as it would
            # break the checksum and store_fname fields. This doesn't
            # prevent removing it thought. Sysadmins can use umask(1) to
            # restrict the permissions further.
            os.chmod(full_path_tmp, 0o444)  # r--r--r--
            os.replace(full_path_tmp, full_path)
        except OSError as e:
            e.add_note(f"_file_write writing {full_path}")
            raise

    @api.model
    def _file_delete(self, fname: str) -> None:
        """ Add ``fname`` to checklist of files to delete. """
        # Deletion may not be done immediately, because this is called within
        # the transaction that could fail later.
        self._mark_for_gc(fname)

    def _mark_for_gc(self, fname: str) -> None:
        """ Add ``fname`` in a checklist for the filestore garbage collection. """
        assert isinstance(self, IrAttachment)
        fname = re.sub(r'[.:]', '', fname).strip('/\\')
        assert not fname.endswith(GC_FILE_SUFFIX)
        # we use a spooldir: add an empty file in the subdirectory 'checklist'
        full_path = os.path.join(self._full_path('checklist'), fname)
        # touch the full_path
        try:
            # create or update last modification date
            open(full_path, 'wb').close()
        except FileNotFoundError:
            # raised when directory does not exist, create the dir and the file
            dirname = os.path.dirname(full_path)
            os.makedirs(dirname, exist_ok=True)
            open(full_path, 'wb').close()

    @api.autovacuum
    def _gc_file_store(self):
        """ Perform the garbage collection of the filestore. """
        assert isinstance(self, IrAttachment)
        if self._storage() != 'file':
            return
        # Fetch the timeouts from the database.
        # GC_GRACE_PERIOD is set to a sensible default, if the DB is configured
        # with a larger value respect it.
        [[grace_db]] = self.env.execute_query(SQL("""
            SELECT MAX(setting::int) / 1000
            FROM pg_settings
            WHERE vartype = 'integer' AND unit = 'ms'
            AND name IN ('idle_in_transaction_session_timeout', 'transaction_timeout')
            AND setting <> '0'
        """))
        self._gc_file_store_unsafe(grace_period=min(GC_GRACE_PERIOD_MAX, max(GC_GRACE_PERIOD, (grace_db or 0) * 2)))

    def _gc_file_store_unsafe(self, grace_period):
        # Generate the file names to check
        limit_time = datetime.now().timestamp() - grace_period

        def files_to_gc():
            for dirpath, _subdirs, filenames in os.walk(self._full_path('checklist')):
                dirname = os.path.basename(dirpath)
                filenames.sort(reverse=True)  # start with files with suffix
                for filename in filenames:
                    check_file = os.path.join(dirpath, filename)
                    fname = f"{dirname}/{filename}"
                    if check_file.endswith(GC_FILE_SUFFIX):
                        # leftover from a previous GC
                        # move the file back if it exists
                        try:
                            os.replace(fname + GC_FILE_SUFFIX, fname)
                        except OSError:
                            _logger.info("filestore gc was interrupted, moving back %s", filename, exc_info=True)
                        else:
                            _logger.info("filestore gc was interrupted, moved back %s", filename)
                        # move the check file back, ignore if file already exists
                        original_check_file = check_file.removesuffix(GC_FILE_SUFFIX)
                        try:
                            if not os.path.exists(original_check_file):
                                os.rename(check_file, original_check_file)
                        except OSError:
                            os.unlink(check_file)
                    elif os.path.getmtime(check_file) < limit_time:
                        # check for write file
                        write_tmp = self._full_path(fname) + WRITE_FILE_SUFFIX
                        if os.path.exists(write_tmp):
                            _logger.info("filestore gc removing partially written file %s", write_tmp)
                            os.unlink(write_tmp)
                        # we can collect the file
                        yield (fname, check_file)

        # Clean up the checklist. The checklist is split in chunks and files are garbage-collected
        # for each chunk.
        checked = 0
        removed = 0
        for name_pairs in split_every(self.env.cr.IN_MAX, files_to_gc()):
            # start a new transaction (see latest data) and release locks of
            # previous loop which we don't want modified during processing
            self.env.cr.commit()
            # determine which files to keep among the checklist
            whitelist = {fname for fname, in self.env.execute_query(
                SQL("SELECT store_fname FROM ir_attachment WHERE store_fname IN %s FOR UPDATE", tuple(p[0] for p in name_pairs)))
            }
            checked += len(name_pairs)

            # remove files, and clean up checklist
            for fname, check_file in name_pairs:
                # If a file is written during the clean up process, we must
                # ensure that it remains on disk. To achieve this on the file
                # system, we are first moving the files and then deleting them
                # after checking if a checkfile did not appear in the meantime.
                full_path = self._full_path(fname)
                del_check_file = check_file + GC_FILE_SUFFIX
                del_full_path = full_path + GC_FILE_SUFFIX
                # 1. Move the check file
                try:
                    if fname in whitelist:
                        os.unlink(check_file)
                        continue
                    else:
                        os.replace(check_file, del_check_file)
                except OSError:
                    _logger.debug("_file_gc could not move %s", check_file)
                    continue
                # 2. Check the mtime of the moved check file
                if not (os.path.getmtime(del_check_file) < limit_time):
                    _logger.debug("_file_gc concurrent write for %s", full_path)
                    os.replace(del_check_file, check_file)  # restore the check file
                    continue
                # 3. Move the file
                try:
                    os.replace(full_path, del_full_path)
                except FileNotFoundError:
                    pass  # check file created but the whole file does not exist
                except OSError:
                    _logger.info("_file_gc could not move %s", full_path, exc_info=True)
                    continue
                # 4. Check if a check file was created in the meantime
                if os.path.exists(check_file):
                    _logger.debug("_file_gc concurrent write during move for %s", full_path)
                    try:  # noqa: SIM105
                        os.replace(del_full_path, full_path)
                    except OSError:
                        _logger.warning("_file_gc failed to move files back, ignore for %s", full_path)
                    os.unlink(del_check_file)
                    continue
                # 5. Remove moved files
                try:
                    os.unlink(del_full_path)
                except FileNotFoundError:
                    pass
                except OSError:
                    _logger.info("_file_gc could not unlink %s", full_path, exc_info=True)
                else:
                    removed += 1
                    _logger.debug("_file_gc unlinked %s", full_path)
                os.unlink(del_check_file)

        _logger.info("filestore gc %d checked, %d removed", checked, removed)

    @api.depends('store_fname', 'db_datas')
    def _compute_raw(self):
        for attach in self:
            if attach.store_fname:
                attach.raw = attach._file_read(attach.store_fname)
            else:
                attach.raw = attach.db_datas

    def _get_pdf_raw(self):
        self.ensure_one()
        if self.type != 'binary':
            return False
        if not self.mimetype.startswith('application/pdf'):
            return False
        return self.raw

    def _inverse_raw(self):
        old_fnames = OrderedSet()
        raw_map = {}

        for attach in self:
            # compute the fields that depend on raw
            bin_data = attach.raw or EMPTY_BINARY
            vals = self._get_datas_related_values(bin_data, attach.mimetype)

            # take current location in filestore to possibly garbage-collect it
            if fname := attach.store_fname:
                old_fnames.add(fname)

            # write as superuser, as user probably does not have write access
            super(IrAttachment, attach.sudo()).write(vals)
            if bin_data and (fname := attach.store_fname):
                raw_map[fname] = bin_data

        if raw_map or old_fnames:
            # before touching the filestore, prevent the GC from
            # running until the end of the transaction
            self.lock_for_update(allow_referencing=True)
        for fname in old_fnames:
            if fname not in raw_map:
                self._file_delete(fname)
        for fname, raw in raw_map.items():
            with raw.open() as f:
                self._file_write(fname, f)

    def _get_datas_related_values(self, data: BinaryValue, mimetype):
        checksum = self._compute_checksum(data)
        try:
            if data:
                index_content = self._index(data, mimetype, checksum=checksum)
            else:
                index_content = False
        except TypeError:
            index_content = self._index(data, mimetype)
        values = {
            'file_size': data.size,
            'checksum': checksum,
            'index_content': index_content,
            'store_fname': False,
            'db_datas': data or False,
        }
        if data and self._storage() != 'db':
            values['store_fname'] = self._file_fname(checksum)
            values['db_datas'] = False
        return values

    @api.model
    def _compute_checksum(self, bin_data):
        """ compute the checksum for the given bytes
            :param bin_data : data in its binary form
        """
        # an empty file has a checksum too (for caching)
        return hashlib.sha1(bin_data or b'').hexdigest()

    @api.model
    def _same_content(self, file1: io.IOBase, file2: io.IOBase) -> bool:
        with contextlib.ExitStack() as exit_stack:
            exit_stack.callback(file1.seek, file1.tell())
            file1.seek(0)
            exit_stack.callback(file2.seek, file2.tell())
            file2.seek(0)
            while True:
                chunk1 = file1.read(io.DEFAULT_BUFFER_SIZE)
                chunk2 = file2.read(io.DEFAULT_BUFFER_SIZE)
                if chunk1 != chunk2:
                    return False
                if not chunk1:
                    break
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
            mimetype = mimetypes.guess_type(values['url'].split('?')[0])[0]
        if not mimetype or mimetype == 'application/octet-stream':
            if raw := values.get('raw'):
                if isinstance(raw, BinaryValue):
                    if mimetype := raw.mimetype:
                        return mimetype
                    raw = raw.content
                assert isinstance(raw, bytes), f"Expecting raw bytes, got {type(raw)}"
                mimetype = guess_mimetype(raw)
        return mimetype.lower() if mimetype else 'application/octet-stream'

    @api.model
    def _postprocess_contents(self, values):
        ICP = self.env['ir.config_parameter'].sudo()
        supported_subtype = (ICP.get_str('base.image_autoresize_extensions') or 'png,jpeg,bmp,tiff').split(',')

        assert 'mimetype' in values and 'datas' not in values, '_check_contents should handle that'
        type_, subtype = values['mimetype'].split('/', 1)
        if type_ != 'image' or subtype not in supported_subtype:
            return values
        raw = values.get('raw')
        if not raw:
            return values

        # Can be set to 0 to skip the resize
        max_resolution = ICP.get_str('base.image_autoresize_max_px') or '1920x1920'
        if str2bool(max_resolution, True):
            try:
                img = image.ImageProcess(raw, verify_resolution=False)

                if not img.image:
                    _logger.info('Post processing ignored : Empty source, SVG, or WEBP')
                    return values

                w, h = img.image.size
                nw, nh = map(int, max_resolution.split('x'))
                if w > nw or h > nh:
                    img = img.resize(nw, nh)
                    if subtype == 'jpeg':  # Do not affect PNGs color palette
                        quality = ICP.get_int('base.image_autoresize_quality', 80)
                        output = img.image_quality(quality)
                    else:
                        output = img.image_quality()
                    values['raw'] = BinaryBytes(output)
            except UserError as e:
                # Catch error during test where we provide fake image
                # raise UserError(_("This file could not be decoded as an image file. Please try with a different file."))
                msg = str(e)  # the exception can be lazy-translated, resolve it here
                _logger.info('Post processing ignored : %s', msg)
        return values

    @api.model
    def _check_contents(self, values):
        # get raw and remove db_datas
        if 'datas' in values:
            warnings.warn("Use raw, datas has beeen removed")
            values.pop('datas')  # ignoring
        raw = values.pop('db_datas', None)
        raw = values.get('raw', raw) or b''
        # make sure we have a BinaryValue in raw (if we have data)
        raw = self._fields['raw'].convert_to_cache(raw, self) or EMPTY_BINARY
        if raw or 'raw' in values:
            values['raw'] = raw

        mimetype = values['mimetype'] = self._compute_mimetype(values)
        xml_like = 'ht' in mimetype or ( # hta, html, xhtml, etc.
                'xml' in mimetype and    # other xml (svg, text/xml, etc)
                not mimetype.startswith('application/vnd.openxmlformats'))  # exception for Office formats
        force_text = xml_like and (
            self.env.context.get('attachments_mime_plainxml')
            or not self.env['ir.ui.view'].sudo(False).has_access('write')
        )
        if force_text:
            values['mimetype'] = 'text/plain'
        if not self.env.context.get('image_no_postprocess'):
            values = self._postprocess_contents(values)
        return values

    @api.model
    def _index(self, bin_data: BinaryValue, file_type: str, checksum=None) -> str | None:
        """ compute the index content of the given binary data.
        This is a python implementation of the unix command 'strings'.
        """
        # compute index_content only for text type
        if file_type and file_type.startswith('text/'):
            word_re = re.compile(rb'[\x20-\x7E]{4,}')
            with bin_data.open() as file:
                # Use readline() with a size limit to avoid unbounded
                # reads on files which may not contain newlines.
                # Note that this could split the indexed content
                # of such files due to the buffer max size.
                return '\n'.join(
                    match.group().decode('ascii')
                    for line in iter(lambda: file.readline(io.DEFAULT_BUFFER_SIZE), b'')
                    for match in word_re.finditer(line)
                )
        return None

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
    res_model = fields.Char('Resource Model')
    res_field = fields.Char('Resource Field')
    res_id = fields.Many2oneReference('Resource ID', model_field='res_model')
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
                                 default=lambda self: self.env.company)
    type = fields.Selection([('url', 'URL'), ('binary', 'File')],
                            string='Type', required=True, default='binary', change_default=True,
                            help="You can either upload a file from your computer or copy/paste an internet link to your file.")
    url = fields.Char('Url', index='btree_not_null', size=1024)
    public = fields.Boolean('Is public document')
    res_access_read = fields.Boolean(
        groups=fields.NO_ACCESS,
        compute=lambda self: self._compute_res_access('read'),
        search=lambda self, operator, value: self._search_res_access('read', operator),
        compute_sudo=True, depends_context=('uid',))
    res_access_write = fields.Boolean(
        groups=fields.NO_ACCESS,
        compute=lambda self: self._compute_res_access('write'),
        search=lambda self, operator, value: self._search_res_access('write', operator),
        compute_sudo=True, depends_context=('uid',))

    # for external access
    access_token = fields.Char('Access Token', groups="base.group_user")

    raw = fields.Binary(string="File Content (raw)", compute='_compute_raw', inverse='_inverse_raw')
    db_datas = fields.Binary('Database Data', attachment=False)
    store_fname = fields.Char('Stored Filename', index=True)
    file_size = fields.Integer('File Size', readonly=True)
    checksum = fields.Char("Checksum/SHA1", size=40, readonly=True)
    mimetype = fields.Char('Mime Type', readonly=True)
    index_content = fields.Text('Indexed Content', readonly=True, prefetch=False)

    _res_idx = models.Index("(res_model, res_id)")

    def _check_serving_attachments(self):
        if self.env.is_admin():
            return
        for attachment in self:
            # restrict writing on attachments that could be served by the
            # ir.http's dispatch exception handling
            # XDO note: if read on sudo, read twice, one for constraints, one for _inverse_raw as user
            if attachment.type == 'binary' and attachment.url:
                has_group = self.env.user.has_group
                if not any(has_group(g) for g in attachment.get_serving_groups()):
                    raise ValidationError(_("Sorry, you are not allowed to write on this document"))

    @api.constrains('res_model', 'res_id')
    def _check_circular_attachment(self):
        for record in self.sudo():
            if record.res_model == 'ir.attachment' and record.id == record.res_id:
                raise ValidationError(_(
                    "You cannot attach an attachment to itself.\n"
                    "Attachment %(record)s cannot have res_id: %(res_id)s",
                    record=record, res_id=record))

    @api.model
    def check(self, mode, values=None):
        """ Restricts the access to an ir.attachment, according to referred mode """
        warnings.warn("Since 19.0, use check_access", DeprecationWarning, stacklevel=2)
        # Always require an internal user (aka, employee) to access to a attachment
        if not (self.env.is_admin() or self.env.user._is_internal()):
            raise AccessError(_("Sorry, you are not allowed to access this document."))
        self.check_access(mode)
        if values and any(self._inaccessible_comodel_records({values.get('res_model'): [values.get('res_id')]}, mode)):
            raise AccessError(_("Sorry, you are not allowed to access this document."))

    def _make_access_error_message(self, operation, domain):
        if not domain.is_false():
            return AccessError(self.env._(
                "Sorry, you are not allowed to access this document. "
                "Please contact your system administrator.\n\n"
                "(Operation: %(operation)s)\n\n"
                "Records: %(records)s, User: %(user)s",
                operation=operation,
                records=self[:6],
                user=self.env.uid,
            ))
        return super()._make_access_error_message(operation, domain)

    def _compute_res_access(self, operation: str):
        """Check access for attachments.

        Rules:

        - If we have `res_model and res_id`, the attachment is accessible if the
          referenced model is accessible. Also, when `res_field != False` and
          the user is not an administrator, we check the access on the field.
        - If we don't have a referenced record, the attachment is accessible to
          the administrator and the creator of the attachment.
        """
        assert operation in ('read', 'write') and self.env.su
        field_name = f'res_access_{operation}'

        # collect the records to check (by model)
        model_ids = defaultdict(set)            # {model_name: set(ids)}
        att_model_ids = []                      # [(att_id, (res_model, res_id))]
        # DLE P173: `test_01_portal_attachment`
        self.fetch(SECURITY_FIELDS)  # fetch only these fields
        user_model = self.sudo(False)
        forbidden_ids = set()
        for attachment in self:
            att_id = attachment.id
            res_model, res_id = attachment.res_model, attachment.res_id
            if not user_model.env.is_system():
                if not res_id and attachment.create_uid.id != self.env.uid:
                    forbidden_ids.add(att_id)
                    continue
                if res_field := attachment.res_field:
                    try:
                        field = self.env[res_model]._fields[res_field]
                    except KeyError:
                        # field does not exist
                        field = None
                    if field is None or not user_model.has_field_access(field, operation):
                        forbidden_ids.add(att_id)
                        continue
            if res_model and res_id:
                model_ids[res_model].add(res_id)
                att_model_ids.append((att_id, (res_model, res_id)))
        forbidden_res_model_id = set(user_model._inaccessible_comodel_records(model_ids, operation))
        forbidden_ids.update(att_id for att_id, res in att_model_ids if res in forbidden_res_model_id)

        if forbidden_ids:
            forbidden = self.browse(forbidden_ids)
            forbidden.invalidate_recordset(SECURITY_FIELDS)  # avoid cache pollution
            for attachment in self:
                attachment[field_name] = attachment.id not in forbidden_ids
        else:
            self[field_name] = True

    def _search_res_access(self, operation, domain_operator):
        assert operation in ('read', 'write') and self.env.su
        if domain_operator != 'in':
            return NotImplemented
        domain = self.env.context.get('search_domain')
        if not isinstance(domain, Domain):
            domain = Domain.TRUE
        sec_domain = Domain.FALSE
        self = self.sudo(False)  # noqa: PLW0642

        # - res_id == False needs to be system user or creator
        res_ids = condition_values(self, 'res_id', domain)
        if not res_ids or False in res_ids:
            if self.env.is_system():
                sec_domain |= Domain('res_id', '=', False)
            else:
                sec_domain |= Domain('res_id', '=', False) & Domain('create_uid', '=', self.env.uid)

        # Search by res_model and res_id, filter using permissions from res_model
        # - res_id != False needs then check access on the linked res_model record
        # - res_field != False needs to check field access on the res_model
        res_model_names = condition_values(self, 'res_model', domain)
        if 0 < len(res_model_names or ()) <= MAX_COMODELS_FOR_DOMAIN:
            env = self.with_context(active_test=False).env
            check_res_fields = not self.env.is_system() and tuple(condition_values(self, 'res_field', domain) or ()) != (False,)
            for res_model_name in res_model_names:
                comodel = env.get(res_model_name)
                if comodel is None:
                    continue
                codomain = Domain('res_model', '=', comodel._name)
                comodel_res_ids = condition_values(self, 'res_id', domain.map_conditions(
                    lambda cond: codomain & cond if cond.field_expr == 'res_model' else cond
                ))
                comodel_domain = Domain('id', 'in', comodel_res_ids) if comodel_res_ids else Domain.TRUE
                if operation != 'read':
                    comodel_domain &= comodel._access_domain(operation).optimize_full(comodel.sudo())
                query = comodel._search(comodel_domain)
                if query.is_empty():
                    continue
                if query.where_clause:
                    codomain &= Domain('res_id', 'in', query)
                if check_res_fields:
                    accessible_fields = [
                        field.name
                        for field in comodel._fields.values()
                        if field.type == 'binary' or (field.relational and field.comodel_name == self._name)
                        if comodel.has_field_access(field, operation)
                    ]
                    accessible_fields.append(False)
                    codomain &= Domain('res_field', 'in', accessible_fields)
                sec_domain |= codomain

            return sec_domain

        # We do not have a small restriction on res_model. We still need to
        # support other queries such as: `('id', 'in' ...)`.
        records = self.sudo().with_context(active_test=False).search_fetch(
            domain & Domain('res_model', '!=', False) & ~sec_domain, SECURITY_FIELDS, order='id', limit=MAX_SEARCH_LIMIT).sudo(False)
        if len(records) == MAX_SEARCH_LIMIT:  # avoid out of memory
            raise ValueError(self.env._("Cannot search, too many attachments"))
        records = records._filtered_access(operation)
        # [('id', 'any!', query_with_ids)] is optimized in sec_domain
        return sec_domain | Domain('id', 'any!', records._as_query(ordered=False))

    def _inaccessible_comodel_records(self, model_and_ids: dict[str, Collection[int]], operation: str):
        # check access rights on the records
        if self.env.su:
            return
        for res_model, res_ids in model_and_ids.items():
            res_ids = OrderedSet(filter(None, res_ids))
            if not res_model or not res_ids:
                # nothing to check
                continue
            # forbid access to attachments linked to removed models as we do not
            # know what persmissions should be checked
            if res_model not in self.env:
                for res_id in res_ids:
                    yield res_model, res_id
                continue
            records = self.env[res_model].browse(res_ids)
            if res_model == 'res.users' and len(records) == 1 and self.env.uid == records.id:
                # by default a user cannot write on itself, despite the list of writeable fields
                # e.g. in the case of a user inserting an image into his image signature
                # we need to bypass this check which would needlessly throw us away
                continue
            try:
                records = records._filtered_access(operation)
            except MissingError:
                records = records.exists()._filtered_access(operation)
            res_ids.difference_update(records._ids)
            for res_id in res_ids:
                yield res_model, res_id

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, *, active_test=True, bypass_access=False):
        assert not self._active_name, "active name not supported on ir.attachment"
        domain = Domain(domain)
        if (
            not self.env.context.get('skip_res_field_check')
            and not any(d.field_expr in ('id', 'res_field') for d in domain.iter_conditions())
            and not bypass_access
        ):
            domain &= Domain('res_field', '=', False)

        domain = domain.optimize_full(self)
        if self.env.su or bypass_access or domain.is_false():
            return super()._search(domain, offset, limit, order, active_test=active_test, bypass_access=bypass_access)
        if self.env.context.get('_generating_sql_for_fields'):
            raise ValueError("Cannot generate SQL for whole ir.attachment")
        if 0 < len(condition_values(self, 'res_model', domain) or ()) <= MAX_COMODELS_FOR_DOMAIN:
            return super()._search(domain, offset, limit, order, active_test=active_test, bypass_access=bypass_access)

        self_sudo = self.sudo().with_context(active_test=False)
        ordered = bool(order)
        if limit is None:
            records = self_sudo.search_fetch(
                domain, SECURITY_FIELDS, order=order).sudo(False)
            return records._filtered_access('read')[offset:]._as_query(ordered)
        # Fetch by small batches
        sub_offset = 0
        limit += offset
        result = []
        if not ordered:
            # By default, order by model to batch access checks.
            order = 'res_model nulls first, id'
        while len(result) < limit:
            records = self_sudo.search_fetch(
                domain,
                SECURITY_FIELDS,
                offset=sub_offset,
                limit=PREFETCH_MAX,
                order=order,
            ).sudo(False)
            result.extend(records._filtered_access('read')._ids)
            if len(records) < PREFETCH_MAX:
                # There are no more records
                break
            sub_offset += PREFETCH_MAX
        return self.browse(result[offset:limit])._as_query(ordered)

    def write(self, vals):
        self.check_access('write')
        if vals.get('res_model') or vals.get('res_id'):
            model_and_ids = defaultdict(OrderedSet)
            if 'res_model' in vals and 'res_id' in vals:
                model_and_ids[vals['res_model']].add(vals['res_id'])
            else:
                for record in self:
                    model_and_ids[vals.get('res_model', record.res_model)].add(vals.get('res_id', record.res_id))
            if any(self._inaccessible_comodel_records(model_and_ids, 'write')):
                raise AccessError(_("Sorry, you are not allowed to access this document."))
        # remove computed field depending of raw
        for field in ('file_size', 'checksum', 'store_fname'):
            vals.pop(field, False)
        if 'mimetype' in vals or 'raw' in vals:
            vals = self._check_contents(vals)
        res = super().write(vals)
        if 'url' in vals or 'type' in vals:
            self._check_serving_attachments()
        return res

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for attachment, vals in zip(self, vals_list):
            if not default.keys() & {'db_datas', 'raw'}:
                # ensure the content is kept and recomputes checksum/store_fname
                vals['raw'] = attachment.raw
        return vals_list

    def unlink(self):
        # First delete in the database, *then* in the filesystem if the
        # database allowed it. Helps avoid errors when concurrent transactions
        # are deleting the same file, and some of the transactions are
        # rolled back by PostgreSQL (due to concurrent updates detection).
        to_delete = OrderedSet(attach.store_fname for attach in self if attach.store_fname)
        res = super().unlink()
        for file_path in to_delete:
            self._file_delete(file_path)

        return res

    @api.model_create_multi
    def create(self, vals_list):
        record_tuple_set = set()

        if self.env.context.get('ir_attachment_from_stream') is not CREATE_FROM_STREAM_FLAG:
            # remove computed field depending of raw
            vals_list = [{
                key: value
                for key, value
                in vals.items()
                if key not in ('file_size', 'checksum', 'store_fname')
            } for vals in vals_list]
        raw_map = {}

        for values in vals_list:
            values = self._check_contents(values)
            if raw := values.pop('raw', None):
                values.update(self._get_datas_related_values(raw, values['mimetype']))
                if fname := values.get('store_fname'):
                    raw_map[fname] = raw

            # 'check()' only uses res_model and res_id from values, and make an exists.
            # We can group the values by model, res_id to make only one query when
            # creating multiple attachments on a single record.
            record_tuple = (values.get('res_model'), values.get('res_id'))
            record_tuple_set.add(record_tuple)

        # don't use possible contextual recordset for check, see commit for details
        model_and_ids = defaultdict(set)
        for res_model, res_id in record_tuple_set:
            model_and_ids[res_model].add(res_id)
        if any(self._inaccessible_comodel_records(model_and_ids, 'write')):
            raise AccessError(_("Sorry, you are not allowed to access this document."))
        records = super().create(vals_list)
        for fname, raw in raw_map.items():
            with raw.open() as f:
                self._file_write(fname, f)
        records._check_serving_attachments()
        return records

    def _post_add_create(self, **kwargs):
        # TODO master: rename to _post_upload, better indicating its usage
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

    def _get_raw_access_token(self):
        """Return a scoped access token for the `raw` field. The token can be
        used with `ir_binary._find_record` to bypass access rights.

        :rtype: str
        """
        self.ensure_one()
        return limited_field_access_token(self, "raw", scope="binary")

    @api.model
    def create_unique(self, vals_list):
        result = self.browse()
        for vals in vals_list:
            try:
                vals = self._check_contents(vals)
            except ValueError:
                raise UserError(_("Attachment is not encoded in base64."))
            checksum = self._compute_checksum(vals['raw'] or b'')
            # Create only if record does not already exist for checksum and mimetype
            result += self.sudo().search([
                ['id', '!=', False],  # No implicit condition on res_field.
                ['checksum', '=', checksum],
                ['mimetype', '=', vals['mimetype']],
            ], limit=1) or self.create(vals)
        return result

    def _generate_access_token(self):
        return str(uuid.uuid4())

    @api.model
    def action_get(self):
        return self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')

    @api.model
    def _get_serve_attachment(self, url, extra_domain=None, order=None):
        domain = [('type', '=', 'binary'), ('url', '=', url)] + (extra_domain or [])
        return self.search(domain, order=order, limit=1)

    @api.model
    def regenerate_assets_bundles(self):
        self.search([
            ('public', '=', True),
            ("url", "=like", "/web/assets/%"),
            ('res_model', '=', 'ir.ui.view'),
            ('res_id', '=', 0),
            ('create_uid', '=', api.SUPERUSER_ID),
        ]).unlink()
        self.env.transaction.invalidate_ormcache('assets')

    def _upload_file(self, file: io.IOBase, create_vals: api.ValuesType) -> typing.Self:
        """
        Create an attachment out of a file.

        The file is read in chunks to compute the checksum, file size,
        and destination path. When it doesn't exist on the file-system
        yet or is not seekable, it is saved in a temporary file in the
        ``path/to/filestore/<dbname>/upload/`` folder. In all cases, the
        file is hard-linked/copied to the correct place in the filestore
        and a new attachment is created for that file.
        """
        if 'raw' in create_vals or 'db_datas' in create_vals:
            e = "Cannot use neither 'raw' nor 'db_datas' with _upload_file."
            raise ValueError(e)

        if self._storage() == 'db':
            return self.create(dict(create_vals, raw=BinaryBytes(file.read())))

        # Check permissions first, so we don't read the entire file if
        # it is gonna fail.
        if any(self._inaccessible_comodel_records(
            model_and_ids={create_vals.get('res_model'): [create_vals.get('res_id')]},
            operation='write',
        )):
            raise AccessError(_("Sorry, you are not allowed to access this document."))

        with contextlib.ExitStack() as exit_stack:

            # For os.link and _same_content, we need the file to be seekable and
            # accessible on the file-system.
            # When it is not, we save it in a named temporary file.
            src_path = getattr(file, 'name', None)
            try:
                if not isinstance(src_path, (str, bytes, os.PathLike)):
                    raise FileNotFoundError(f"not a path: {src_path}")
                open(src_path, 'rb').close()  # check we can read it
                file.seek(0)
            except OSError:  # not accessible/seekable
                upload_dir = self._full_path('upload')
                os.makedirs(upload_dir, 0o755, exist_ok=True)
                file_upload = exit_stack.enter_context(
                    tempfile.NamedTemporaryFile(
                        dir=upload_dir,
                        prefix="{model}-{id}-{uid}-".format(
                            model=create_vals.get('res_model', ''),
                            id=create_vals.get('res_id', ''),
                            uid=self.env.uid,
                        ),
                        suffix='.part',
                    ),
                )
                src_path = file_upload.name
            else:
                file_upload = None

            # Read the file's content in chunks to compute its checksum,
            # size and destination file name. Save it in the temporary
            # file if necessary.
            # Similar to `_compute_checksum`.
            computed_fields = {'file_size': 0}
            sha = hashlib.sha1()
            while chunk := file.read(io.DEFAULT_BUFFER_SIZE):  # 16kiB
                sha.update(chunk)
                computed_fields['file_size'] += len(chunk)
                if file_upload:
                    file_upload.write(chunk)
            if file_upload:
                file_upload.flush()
            else:
                # reset the position to the beginning to save the data
                file.seek(0)
            computed_fields['checksum'] = sha.hexdigest()
            computed_fields['store_fname'] = self._file_fname(computed_fields['checksum'])
            if 'mimetype' not in create_vals:
                computed_fields['mimetype'] = guess_file_mimetype(src_path)
            # check the destination (overrides of _file_fname)
            dst_path = self._full_path(computed_fields['store_fname'])
            if computed_fields['store_fname'] not in dst_path:
                # overwrite of _file_fname or _full_path are possibly not local
                # anymore, use the super
                return self.create(dict(create_vals, raw=BinaryBytes(file.read())))

            # The order of the next lines matters for _gc_file_store. It
            # MUST be create => _mark_for_gc => link => commit/rollback.
            # Similar to `_file_write`.
            attach = (
                self.with_context(ir_attachment_from_stream=CREATE_FROM_STREAM_FLAG)
                    .create(create_vals | computed_fields)
                    .with_env(self.env)
            )
            self._mark_for_gc(attach.store_fname)
            try:
                os.link(src_path, dst_path)  # Fast hardlink
                os.chmod(dst_path, 0o444)  # r--r--r--
            except OSError:
                self._file_write(computed_fields['store_fname'], file_upload or file)

        attach.index_content = attach._index(attach.raw, attach.mimetype, attach.checksum)
        return attach

    def _to_http_stream(self):
        """ Create a :class:`~Stream`: from an ir.attachment record. """
        self.ensure_one()

        kw = dict(
            mimetype=self.mimetype,
            download_name=self.name,
            etag=self.checksum,
            public=self.public,
        )

        if self.store_fname and (path := self._full_path(self.store_fname)):
            # Try to read directly from the file system without reading the file
            try:
                stat = os.stat(path)
                return Stream(
                    **kw,
                    type='path',
                    path=path,
                    last_modified=stat.st_mtime,
                    size=stat.st_size,
                )
            except OSError:
                pass

        elif self.url:
            return Stream(type='url', url=self.url, **kw)

        data = self.raw.content
        return Stream(
            type='data',
            data=data,
            last_modified=self.write_date,
            size=len(data),
            **kw,
        )

    def _is_remote_source(self):
        self.ensure_one()
        return self.url and not self.file_size and self.url.startswith(('http://', 'https://', 'ftp://'))

    def _can_return_content(self, field_name=None, access_token=None):
        attachment_sudo = self.sudo().with_context(prefetch_fields=False)
        if access_token:
            if not consteq(attachment_sudo.access_token or "", access_token):
                raise AccessError("Invalid access token")  # pylint: disable=missing-gettext
            return True
        if attachment_sudo.public:
            return True
        if self.env.user._is_portal():
            # Check the read access on the record linked to the attachment
            # eg: Allow to download an attachment on a task from /my/tasks/task_id
            self.check_access('read')
            return True
        return super()._can_return_content(field_name, access_token)

    def _migrate_remote_to_local(self):
        if self.type == 'binary':
            return
        if self.type == 'url':
            raise ValidationError(_("URL attachment (%s) shouldn't be migrated to local.", self.id))


class LocalBinaryFile(BinaryValue):
    """Lazily loaded file."""
    __slots__ = ('__content', '__mimetype', '__path', '__stat')

    def __init__(self, path: str, model: IrAttachment):
        """ Open a file as a binary value.

        :param path: absolute path to the file
        :param model: model to check the path
        :raise OSError: if the file cannot be opened
        """
        path = model._full_path(path)
        self.__path = path
        self.__stat = os.stat(path)  # checks that the file exists
        if not stat.S_ISREG(self.__stat.st_mode):
            raise FileNotFoundError(f"Path is not a regular file: {path}")
        self.__content: bytes | None = None
        self.__mimetype: str | None = None

    def open(self):
        assert isinstance(self, LocalBinaryFile)
        if self.__content is not None:
            return super().open()
        # open the file
        return open(self.__path, 'rb')

    @property
    def content(self) -> bytes:
        if self.__content is None:
            with self.open() as f:
                self.__content = f.read()
        return self.__content

    @property
    def mimetype(self):
        if self.__mimetype is None:
            self.__mimetype = guess_file_mimetype(self.__path)
        return self.__mimetype

    @property
    def size(self):
        return self.__stat.st_size

    def __repr__(self):
        return f"LocalBinaryFile({self.__path!r})"
