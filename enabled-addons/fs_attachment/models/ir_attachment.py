# Copyright 2017-2013 Camptocamp SA
# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from __future__ import annotations

import io
import logging
import mimetypes
import os
import re
import time
from contextlib import closing, contextmanager
from pathlib import Path

import fsspec  # pylint: disable=missing-manifest-dependency
import psycopg2
from slugify import slugify  # pylint: disable=missing-manifest-dependency

import odoo
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.osv.expression import AND, OR, normalize_domain

from .strtobool import strtobool

_logger = logging.getLogger(__name__)


REGEX_SLUGIFY = r"[^-a-z0-9_]+"

FS_FILENAME_RE_PARSER = re.compile(
    r"^(?P<name>.+)-(?P<id>\d+)-(?P<version>\d+)(?P<extension>\..+)$"
)


def is_true(strval):
    return bool(strtobool(strval or "0"))


def clean_fs(files):
    _logger.info("cleaning old files from filestore")
    for full_path in files:
        if os.path.exists(full_path):
            try:
                os.unlink(full_path)
            except OSError:
                _logger.info(
                    "_file_delete could not unlink %s", full_path, exc_info=True
                )


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    fs_filename = fields.Char(
        "File Name into the filesystem storage",
        help="The name of the file in the filesystem storage."
        "To preserve the mimetype and the meaning of the filename"
        "the filename is computed from the name and the extension",
        readonly=True,
    )

    internal_url = fields.Char(
        "Internal URL",
        compute="_compute_internal_url",
        help="The URL to access the file from the server.",
    )

    fs_url = fields.Char(
        "Filesystem URL",
        compute="_compute_fs_url",
        help="The URL to access the file from the filesystem storage.",
        store=True,
    )
    fs_url_path = fields.Char(
        "Filesystem URL Path",
        compute="_compute_fs_url_path",
        help="The path to access the file from the filesystem storage.",
    )
    fs_storage_code = fields.Char(
        "Filesystem Storage Code",
        related="fs_storage_id.code",
        store=True,
    )
    fs_storage_id = fields.Many2one(
        "fs.storage",
        "Filesystem Storage",
        compute="_compute_fs_storage_id",
        help="The storage where the file is stored.",
        store=True,
        ondelete="restrict",
    )

    @api.depends("name")
    def _compute_internal_url(self) -> None:
        for rec in self:
            filename, extension = os.path.splitext(rec.name)
            # determine if the file is an image
            pfx = "/web/content"
            if rec.mimetype and rec.mimetype.startswith("image/"):
                pfx = "/web/image"

            if not extension:
                extension = mimetypes.guess_extension(rec.mimetype)
            rec.internal_url = f"{pfx}/{rec.id}/{filename}{extension}"

    @api.depends("fs_filename")
    def _compute_fs_url(self) -> None:
        for rec in self:
            new_url = None
            actual_url = rec.fs_url or None
            if rec.fs_filename:
                new_url = self.env["fs.storage"]._get_url_for_attachment(rec)
            # ensure we compare value of same type and not None with False
            new_url = new_url or None
            if new_url != actual_url:
                rec.fs_url = new_url

    @api.depends("fs_filename")
    def _compute_fs_url_path(self) -> None:
        for rec in self:
            rec.fs_url_path = None
            if rec.fs_filename:
                rec.fs_url_path = self.env["fs.storage"]._get_url_for_attachment(
                    rec, exclude_base_url=True
                )

    @api.depends("fs_filename")
    def _compute_fs_storage_id(self):
        for rec in self:
            if rec.store_fname:
                code = rec.store_fname.partition("://")[0]
                fs_storage = self.env["fs.storage"].sudo().get_by_code(code)
                if fs_storage != rec.fs_storage_id:
                    rec.fs_storage_id = fs_storage
            elif rec.fs_storage_id:
                rec.fs_storage_id = None

    @staticmethod
    def _is_storage_disabled(storage=None, log=True):
        msg = "Storages are disabled (see environment configuration)."
        if storage:
            msg = f"Storage '{storage}' is disabled (see environment configuration)."
        is_disabled = is_true(os.environ.get("DISABLE_ATTACHMENT_STORAGE"))
        if is_disabled and log:
            _logger.warning(msg)
        return is_disabled

    def _get_storage_force_db_config(self):
        return self.env["fs.storage"].get_force_db_for_default_attachment_rules(
            self._storage()
        )

    def _store_in_db_instead_of_object_storage_domain(self):
        """Return a domain for attachments that must be forced to DB

        Read the docstring of ``_store_in_db_instead_of_object_storage`` for
        more details.

        Used in ``force_storage_to_db_for_special_fields`` to find records
        to move from the object storage to the database.

        The domain must be inline with the conditions in
        ``_store_in_db_instead_of_object_storage``.
        """
        domain = []
        storage_config = self._get_storage_force_db_config()
        for mimetype_key, limit in storage_config.items():
            part = [("mimetype", "=like", f"{mimetype_key}%")]
            if limit:
                part = AND([part, [("file_size", "<=", limit)]])
            # OR simplifies to [(1, '=', 1)] if a domain being OR'ed is empty
            domain = OR([domain, part]) if domain else part
        return domain

    def _store_in_db_instead_of_object_storage(self, data, mimetype):
        """Return whether an attachment must be stored in db

        When we are using an Object Storage. This is sometimes required
        because the object storage is slower than the database/filesystem.

        Small images (128, 256) are used in Odoo in list / kanban views. We
        want them to be fast to read.
        They are generally < 50KB (default configuration) so they don't take
        that much space in database, but they'll be read much faster than from
        the object storage.

        The assets (application/javascript, text/css) are stored in database
        as well whatever their size is:

        * a database doesn't have thousands of them
        * of course better for performance
        * better portability of a database: when replicating a production
          instance for dev, the assets are included

        The configuration can be modified on the fs.storage record, in the
        field ``force_db_for_default_attachment_rules``, as a dictionary, for
        instance::

            {"image/": 51200, "application/javascript": 0, "text/css": 0}

        Where the key is the beginning of the mimetype to configure and the
        value is the limit in size below which attachments are kept in DB.
        0 means no limit.

        These limits are applied only if the storage is the default one for
        attachments (see ``_storage``).

        The conditions are also applied into the domain of the method
        ``_store_in_db_instead_of_object_storage_domain`` used to move records
        from a filesystem storage to the database.

        """
        if self._is_storage_disabled():
            return True
        storage_config = self._get_storage_force_db_config()
        for mimetype_key, limit in storage_config.items():
            if mimetype.startswith(mimetype_key):
                if not limit:
                    return True
                bin_data = data
                return len(bin_data) <= limit
        return False

    def _get_datas_related_values(self, data, mimetype):
        storage = self.env.context.get("storage_location") or self._storage()
        if data and storage in self._get_storage_codes():
            if self._store_in_db_instead_of_object_storage(data, mimetype):
                # compute the fields that depend on datas
                bin_data = data
                values = {
                    "file_size": len(bin_data),
                    "checksum": self._compute_checksum(bin_data),
                    "index_content": self._index(bin_data, mimetype),
                    "store_fname": False,
                    "db_datas": data,
                }
                return values
        return super(
            IrAttachment, self.with_context(mimetype=mimetype)
        )._get_datas_related_values(data, mimetype)

    ###########################################################
    # Odoo methods that we override to use the object storage #
    ###########################################################
    @api.model
    def _storage(self):
        # We check if a filesystem storage is configured for attachments
        storage = self.env["fs.storage"].get_default_storage_code_for_attachments()
        if not storage:
            # If not, we use the default storage configured into odoo
            storage = super()._storage()
        return storage

    @api.model_create_multi
    def create(self, vals_list):
        """
        Storage may depend on resource field, but the method calling _storage
        (_get_datas_related_values) does not take all vals, just the mimetype.
        The only way to give res_field and res_model to _storage method
        is to pass them into the context, and perform 1 create call per record
        to create.
        """
        vals_list_no_model = []
        attachments = self.env["ir.attachment"]
        for vals in vals_list:
            if vals.get("res_model"):
                attachment = super(
                    IrAttachment,
                    self.with_context(
                        attachment_res_model=vals.get("res_model"),
                        attachment_res_field=vals.get("res_field"),
                    ),
                ).create(vals)
                attachments += attachment
            else:
                vals_list_no_model.append(vals)
        atts = super().create(vals_list_no_model)
        attachments |= atts
        attachments._enforce_meaningful_storage_filename()
        return attachments

    def write(self, vals):
        if not self:
            return super().write(vals)
        if ("datas" in vals or "raw" in vals) and not (
            "name" in vals or "mimetype" in vals
        ):
            mimetype = self._compute_mimetype(vals)
            if mimetype and mimetype != "application/octet-stream":
                vals["mimetype"] = mimetype
            else:
                # When we write on an attachment, if the mimetype is not provided, it
                # will be computed from the name. The problem is that if you assign a
                # value to the field ``datas`` or ``raw``, the name is not provided
                # nor the mimetype, so the mimetype will be set to ``application/octet-
                # stream``.
                # We want to avoid this, so we take the mimetype of the first attachment
                # and we set it on all the attachments if they all have the same
                # mimetype.
                # If they don't have the same mimetype, we raise an error.
                # OPW-3277070
                mimetypes = self.mapped("mimetype")
                if len(set(mimetypes)) == 1:
                    vals["mimetype"] = mimetypes[0]
                else:
                    raise UserError(
                        _(
                            "You can't write on multiple attachments with different "
                            "mimetypes at the same time."
                        )
                    )
        for rec in self:
            # As when creating a new attachment, we must pass the res_field
            # and res_model into the context hence sadly we must perform 1 call
            # for each attachment
            super(
                IrAttachment,
                rec.with_context(
                    attachment_res_model=vals.get("res_model") or rec.res_model,
                    attachment_res_field=vals.get("res_field") or rec.res_field,
                ),
            ).write(vals)

        if "name" in vals:
            self._enforce_meaningful_storage_filename()

        return True

    @api.model
    def _file_read(self, fname):
        if self._is_file_from_a_storage(fname):
            return self._storage_file_read(fname)
        else:
            return super()._file_read(fname)

    @api.model
    def _file_write(self, bin_data, checksum):
        location = self.env.context.get("storage_location") or self._storage()
        if location in self._get_storage_codes():
            filename = self._storage_file_write(bin_data)
        else:
            filename = super()._file_write(bin_data, checksum)
        return filename

    @api.model
    def _file_delete(self, fname) -> None:  # pylint: disable=missing-return
        if self._is_file_from_a_storage(fname):
            cr = self.env.cr
            # using SQL to include files hidden through unlink or due to record
            # rules
            cr.execute(
                "SELECT COUNT(*) FROM ir_attachment WHERE store_fname = %s", (fname,)
            )
            count = cr.fetchone()[0]
            if not count:
                self._storage_file_delete(fname)
        else:
            super()._file_delete(fname)

    def _set_attachment_data(self, asbytes) -> None:  # pylint: disable=missing-return
        super()._set_attachment_data(asbytes)
        self._enforce_meaningful_storage_filename()

    ##############################################
    # Internal methods to use the object storage #
    ##############################################
    @api.model
    def _storage_file_read(self, fname: str) -> bytes | None:
        """Read the file from the filesystem storage"""
        fs, _storage, fname = self._fs_parse_store_fname(fname)
        try:
            with fs.open(fname, "rb") as f:
                return f.read()
        except OSError:
            _logger.info(
                "Error reading %s on storage %s", fname, _storage, exc_info=True
            )
        return b""

    def _storage_write_option(self, fs):
        return {}

    @api.model
    def _storage_file_write(self, bin_data: bytes) -> str:
        """Write the file to the filesystem storage"""
        storage = self.env.context.get("storage_location") or self._storage()
        fs = self._get_fs_storage_for_code(storage)
        path = self._get_fs_path(storage, bin_data)
        dirname = os.path.dirname(path)
        if not fs.exists(dirname):
            fs.makedirs(dirname)
        fname = f"{storage}://{path}"
        kwargs = self._storage_write_option(fs)
        with fs.open(path, "wb", **kwargs) as f:
            f.write(bin_data)
        self._fs_mark_for_gc(fname)
        return fname

    @api.model
    def _storage_file_delete(self, fname):
        """Delete the file from the filesystem storage

        It's safe to use the fname (the store_fname) to delete the file because
        even if it's the full path to the file, the gc will only delete the file
        if they belong to the configured storage directory path.
        """
        self._fs_mark_for_gc(fname)

    @api.model
    def _get_fs_path(self, storage_code: str, bin_data: bytes) -> str:
        """Compute the path to store the file in the filesystem storage"""
        key = self.env.context.get("force_storage_key")
        if not key:
            key = self._compute_checksum(bin_data)
        if self.env["fs.storage"]._must_optimize_directory_path(storage_code):
            # Generate a unique directory path based on the file's hash
            key = os.path.join(key[:2], key[2:4], key)
        # Generate a unique directory path based on the file's hash
        return key

    def _build_fs_filename(self):
        """Build the filename to store in the filesystem storage

        The filename is computed from the name, the extension and a version
        number. The version number is incremented each time we build a new
        filename. To know if a filename has already been build, we check if
        the fs_filename field is set. If it is set, we increment the version
        number. The version number is taken from the computed filename.

        The format of the filename is:
        <slugified name>-<id>-<version>.<extension>
        """
        self.ensure_one()
        filename, extension = os.path.splitext(self.name)
        if not extension:
            extension = mimetypes.guess_extension(self.mimetype)
        version = 0
        if self.fs_filename:
            parsed = self._parse_fs_filename(self.fs_filename)
            if parsed:
                version = parsed[2] + 1
        return "{}{}".format(
            slugify(
                f"{filename}-{self.id}-{version}",
                regex_pattern=REGEX_SLUGIFY,
            ),
            extension,
        )

    def _enforce_meaningful_storage_filename(self) -> None:
        """Enforce meaningful filename for files stored in the filesystem storage

        The filename of the file in the filesystem storage is computed from
        the mimetype and the name of the attachment. This method is called
        when an attachment is created to ensure that the filename of the file
        in the filesystem keeps the same meaning as the name of the attachment.

        Keeping the same meaning and mimetype is important to also ease to provide
        a meaningful and SEO friendly URL to the file in the filesystem storage.
        """
        for attachment in self:
            if not self._is_file_from_a_storage(attachment.store_fname):
                continue
            fs, storage, filename = attachment._get_fs_parts()

            if self.env["fs.storage"]._must_use_filename_obfuscation(storage):
                attachment.fs_filename = filename
                continue
            new_filename = attachment._build_fs_filename()
            # we must keep the same full path as the original filename
            new_filename_with_path = os.path.join(
                os.path.dirname(filename), new_filename
            )
            fs.rename(filename, new_filename_with_path)
            attachment.fs_filename = new_filename
            # we need to update the store_fname with the new filename by
            # calling the write method of the field since the write method
            # of ir_attachment prevent normal write on store_fname
            # flake8: noqa: E231
            attachment._force_write_store_fname(f"{storage}://{new_filename_with_path}")
            self._fs_mark_for_gc(attachment.store_fname)

    def _force_write_store_fname(self, store_fname):
        """Force the write of the store_fname field

        The base implementation of the store_fname field prevent the write
        of the store_fname field. This method bypass this limitation by
        calling the write method of the field directly.
        """
        self._fields["store_fname"].write(self, store_fname)

    @api.model
    def _get_fs_storage_for_code(
        self,
        code: str,
    ) -> fsspec.AbstractFileSystem | None:
        """Return the filesystem for the given storage code"""
        fs = self.env["fs.storage"].get_fs_by_code(code)
        if not fs:
            raise SystemError(f"No Filesystem storage for code {code}")
        return fs

    @api.model
    def _fs_parse_store_fname(
        self, fname: str
    ) -> tuple[fsspec.AbstractFileSystem, str, str]:
        """Return the filesystem, the storage code and the path for the given fname

        :param fname: the fname to parse
        :param base: if True, return the base filesystem
        """
        partition = fname.partition("://")
        storage_code = partition[0]
        fs = self._get_fs_storage_for_code(storage_code)
        fname = partition[2]
        return fs, storage_code, fname

    @api.model
    def _parse_fs_filename(self, filename: str) -> tuple[str, int, int, str] | None:
        """Parse the filename and return the name, id, version and extension
        <name-without-extension>-<id>-<version>.<extension>
        """
        if not filename:
            return None
        filename = os.path.basename(filename)
        match = FS_FILENAME_RE_PARSER.match(filename)
        if not match:
            return None
        name, res_id, version, extension = match.groups()
        return name, int(res_id), int(version), extension

    @api.model
    def _is_file_from_a_storage(self, fname):
        if not fname:
            return False
        for storage_code in self._get_storage_codes():
            if self._is_storage_disabled(storage_code):
                continue
            uri = f"{storage_code}://"
            if fname.startswith(uri):
                return True
        return False

    @api.model
    def _fs_mark_for_gc(self, fname):
        """Mark the file for deletion

        The file will be deleted by the garbage collector if it's no more
        referenced by any attachment. We use a garbage collector to enforce
        the transaction mechanism between Odoo and the filesystem storage.
        Files are added to the garbage collector when:
        - each time a file is created in the filesystem storage
        - an attachment is deleted

        Whatever the result of the current transaction, the information of files
        marked for deletion is stored in the database.

        When the garbage collector is called, it will check if the file is still
        referenced by an attachment. If not, the file is physically deleted from
        the filesystem storage.

        If the creation of the attachment fails, since the file is marked for
        deletion when it's written into the filesystem storage, it will be
        deleted by the garbage collector.

        If the content of the attachment is updated, we always create a new file.
        This new file is marked for deletion and the old one too. If the transaction
        succeeds, the old file is deleted by the garbage collector since it's no
        more referenced by any attachment. If the transaction fails, the old file
        is not deleted since it's still referenced by the attachment but the new
        file is deleted since it's marked for deletion and not referenced.
        """
        self.env["fs.file.gc"]._mark_for_gc(fname)

    def _get_fs_parts(
        self,
    ) -> tuple[fsspec.AbstractFileSystem, str, str] | tuple[None, None, None]:
        """Return the filesystem, the storage code and the path for the
        current attachment
        """
        if not self.store_fname:
            return None, None, None
        return self._fs_parse_store_fname(self.store_fname)

    def open(
        self,
        mode="rb",
        block_size=None,
        cache_options=None,
        compression=None,
        new_version=True,
        **kwargs,
    ) -> io.IOBase:
        """
        Return a file-like object from the filesystem storage where the attachment
        content is stored.

        In read mode, this method works for all attachments, even if the content
        is stored in the database or into the odoo filestore or a filesystem storage.

        The resultant instance must function correctly in a context ``with``
        block.

        (parameters are ignored in the case of the database storage).

        Parameters
        ----------
        path: str
            Target file
        mode: str like 'rb', 'w'
            See builtin ``open()``
        block_size: int
            Some indication of buffering - this is a value in bytes
        cache_options : dict, optional
            Extra arguments to pass through to the cache.
        compression: string or None
            If given, open file using compression codec. Can either be a compression
            name (a key in ``fsspec.compression.compr``) or "infer" to guess the
            compression from the filename suffix.
        new_version: bool
            If True, and mode is 'w', create a new version of the file.
            If False, and mode is 'w', overwrite the current version of the file.
            This flag is True by default to avoid data loss and ensure transaction
            mechanism between Odoo and the filesystem storage.
        encoding, errors, newline: passed on to TextIOWrapper for text mode

        Returns
        -------
        A file-like object

        TODO if open with 'w' in mode, we could use a buffered IO detecting that
        the content is modified and invalidating the attachment cache...
        """
        self.ensure_one()
        return AttachmentFileLikeAdapter(
            self,
            mode=mode,
            block_size=block_size,
            cache_options=cache_options,
            compression=compression,
            new_version=new_version,
            **kwargs,
        )

    @contextmanager
    def _do_in_new_env(self, new_cr=False):
        """Context manager that yields a new environment

        Using a new Odoo Environment thus a new PG transaction.
        """
        if new_cr:
            registry = odoo.modules.registry.Registry.new(self.env.cr.dbname)
            with closing(registry.cursor()) as cr:
                try:
                    yield self.env(cr=cr)
                except Exception:
                    cr.rollback()
                    raise
                else:
                    # disable pylint error because this is a valid commit,
                    # we are in a new env
                    cr.commit()  # pylint: disable=invalid-commit
        else:
            # make a copy
            yield self.env()

    def _get_storage_codes(self):
        """Get the list of filesystem storage active in the system"""
        return self.env["fs.storage"].sudo().get_storage_codes()

    def _get_x_sendfile_path(self):
        """Get the path to use for X-Accel-Redirect"""
        self.ensure_one()
        url_path = self.fs_url_path
        storage_code = self.fs_storage_code
        if not url_path:
            raise RuntimeError(
                f"The attachment {self.id} is not stored in a filesystem storage."
            )
        path = Path("/") / storage_code / url_path.lstrip("/")
        return str(path)

    def _fs_use_x_sendfile(self):
        """Return whether to use X-Sendfile to serve the internal URL"""
        self.ensure_one()
        return (
            self.fs_url_path and self.fs_storage_id.use_x_sendfile_to_serve_internal_url
        )

    ################################
    # useful methods for migration #
    ################################

    def _move_attachment_to_store(self):
        self.ensure_one()
        _logger.info("inspecting attachment %s (%d)", self.name, self.id)
        fname = self.store_fname
        storage = fname.partition("://")[0]
        if self._is_storage_disabled(storage):
            fname = False
        if fname:
            # migrating from filesystem filestore
            # or from the old 'store_fname' without the bucket name
            _logger.info("moving %s on the object storage", fname)
            self.write(
                {
                    "datas": self.datas,
                    # this is required otherwise the
                    # mimetype gets overriden with
                    # 'application/octet-stream'
                    # on assets
                    "mimetype": self.mimetype,
                }
            )
            _logger.info("moved %s on the object storage", fname)
            return self._full_path(fname)
        elif self.db_datas:
            _logger.info("moving on the object storage from database")
            self.write({"datas": self.datas})

    @api.model
    def force_storage(self):
        if not self.env["res.users"].browse(self.env.uid)._is_admin():
            raise AccessError(_("Only administrators can execute this action."))
        location = self.env.context.get("storage_location") or self._storage()
        if location not in self._get_storage_codes():
            return super().force_storage()
        self._force_storage_to_object_storage()

    @api.model
    def force_storage_to_db_for_special_fields(
        self, new_cr=False, storage: str | None = None
    ):
        """Migrate special attachments from Object Storage back to database

        The access to a file stored on the objects storage is slower
        than a local disk or database access. For attachments like
        image_small that are accessed in batch for kanban views, this
        is too slow. We store this type of attachment in the database.

        This method can be used when migrating a filestore where all the files,
        including the special files (assets, image_small, ...) have been pushed
        to the Object Storage and we want to write them back in the database.

        It is not called anywhere, but can be called by RPC or scripts.
        """
        if not storage:
            storage = self._storage()
        if self._is_storage_disabled(storage):
            _logger.warning(
                "Storage '%s' is disabled, skipping migration of attachments to DB",
                storage,
            )
            return
        if storage not in self._get_storage_codes():
            _logger.warning(
                "Storage '%s' is not configured, "
                "skipping migration of attachments to DB",
                storage,
            )
            return

        domain = AND(
            (
                normalize_domain(
                    [
                        ("store_fname", "=like", f"{storage}://%"),
                        # for res_field, see comment in
                        # _force_storage_to_object_storage
                        "|",
                        ("res_field", "=", False),
                        ("res_field", "!=", False),
                    ]
                ),
                normalize_domain(self._store_in_db_instead_of_object_storage_domain()),
            )
        )

        with self._do_in_new_env(new_cr=new_cr) as new_env:
            model_env = new_env["ir.attachment"].with_context(prefetch_fields=False)
            attachment_ids = model_env.search(domain).ids
            if not attachment_ids:
                return
            total = len(attachment_ids)
            start_time = time.time()
            _logger.info(
                "Moving %d attachments from %s to DB for fast access", total, storage
            )
            current = 0
            for attachment_id in attachment_ids:
                current += 1
                # if we browse attachments outside of the loop, the first
                # access to 'datas' will compute all the 'datas' fields at
                # once, which means reading hundreds or thousands of files at
                # once, exhausting memory
                attachment = model_env.browse(attachment_id)
                # this write will read the datas from the Object Storage and
                # write them back in the DB (the logic for location to write is
                # in the 'datas' inverse computed field)
                # we need to write the mimetype too, otherwise it will be
                # overwritten with 'application/octet-stream' on assets. On each
                # write, the mimetype is recomputed if not given. If we don't
                # pass it nor the name, the mimetype will be set to the default
                # value 'application/octet-stream' on assets.
                attachment.write({"datas": attachment.datas})
                if current % 100 == 0 or total - current == 0:
                    _logger.info(
                        "attachment %s/%s after %.2fs",
                        current,
                        total,
                        time.time() - start_time,
                    )

    @api.model
    def _force_storage_to_object_storage(self, new_cr=False):
        _logger.info("migrating files to the object storage")
        storage = self.env.context.get("storage_location") or self._storage()
        if self._is_storage_disabled(storage):
            return
        # The weird "res_field = False OR res_field != False" domain
        # is required! It's because of an override of _search in ir.attachment
        # which adds ('res_field', '=', False) when the domain does not
        # contain 'res_field'.
        # https://github.com/odoo/odoo/blob/9032617120138848c63b3cfa5d1913c5e5ad76db/
        # odoo/addons/base/ir/ir_attachment.py#L344-L347
        domain = [
            "!",
            ("store_fname", "=like", f"{storage}://%"),
            "|",
            ("res_field", "=", False),
            ("res_field", "!=", False),
        ]
        # We do a copy of the environment so we can workaround the cache issue
        # below. We do not create a new cursor by default because it causes
        # serialization issues due to concurrent updates on attachments during
        # the installation
        with self._do_in_new_env(new_cr=new_cr) as new_env:
            model_env = new_env["ir.attachment"]
            ids = model_env.search(domain).ids
            files_to_clean = []
            for attachment_id in ids:
                try:
                    with new_env.cr.savepoint():
                        # check that no other transaction has
                        # locked the row, don't send a file to storage
                        # in that case
                        self.env.cr.execute(
                            "SELECT id "
                            "FROM ir_attachment "
                            "WHERE id = %s "
                            "FOR UPDATE NOWAIT",
                            (attachment_id,),
                            log_exceptions=False,
                        )

                        # This is a trick to avoid having the 'datas'
                        # function fields computed for every attachment on
                        # each iteration of the loop. The former issue
                        # being that it reads the content of the file of
                        # ALL the attachments on each loop.
                        new_env.clear()
                        attachment = model_env.browse(attachment_id)
                        path = attachment._move_attachment_to_store()
                        if path:
                            files_to_clean.append(path)
                except psycopg2.OperationalError:
                    _logger.error(
                        "Could not migrate attachment %s to S3", attachment_id
                    )

            # delete the files from the filesystem once we know the changes
            # have been committed in ir.attachment
            if files_to_clean:
                new_env.cr.commit()
                clean_fs(files_to_clean)


class AttachmentFileLikeAdapter:
    """
    This class is a wrapper class around the ir.attachment model. It is used to
    open the ir.attachment as a file and to read/write data to it.

    When the content of the file is stored into the odoo filestore or in a
    filesystem storage, this object allows you to read/write the content from
    the file in a direct way without having to read/write the whole file into
    memory. When the content of the file is stored into database, this content
    is read/written from/into a buffer in memory.

    Parameters
    ----------
    attachment : ir.attachment
        The attachment to open as a file.
    mode: str like 'rb', 'w'
            See builtin ``open()``
    block_size: int
        Some indication of buffering - this is a value in bytes
    cache_options : dict, optional
        Extra arguments to pass through to the cache.
    compression: string or None
        If given, open file using compression codec. Can either be a compression
        name (a key in ``fsspec.compression.compr``) or "infer" to guess the
        compression from the filename suffix.
    new_version: bool
        If True, and mode is 'w', create a new version of the file.
        If False, and mode is 'w', overwrite the current version of the file.
        This flag is True by default to avoid data loss and ensure transaction
        mechanism between Odoo and the filesystem storage.
    encoding, errors, newline: passed on to TextIOWrapper for text mode

    You can use this class to adapt an attachment object as a file in 2 ways:
     * as a context manager wrapping the attachment object as a file
     * or as a nomral utility class

    Examples

    >>> with AttachmentFileLikeAdapter(attachment, mode="rb") as f:
    ...     f.read()
    b'Hello World'
    # at the end of the context manager, the file is closed
    >>> f = AttachmentFileLikeAdapter(attachment, mode="rb")
    >>> f.read()
    b'Hello World'
    # you have to close the file manually
    >>> f.close()

    """

    def __init__(
        self,
        attachment: IrAttachment,
        mode: str = "rb",
        block_size: int | None = None,
        cache_options: dict | None = None,
        compression: str | None = None,
        new_version: bool = False,
        **kwargs,
    ):
        self._attachment = attachment
        self._mode = mode
        self._block_size = block_size
        self._cache_options = cache_options
        self._compression = compression
        self._new_version = new_version
        self._kwargs = kwargs

        # state attributes
        self._file: io.IOBase | None = None
        self._filesystem: fsspec.AbstractFileSystem | None = None
        self._new_store_fname: str | None = None

    @property
    def attachment(self) -> IrAttachment:
        """The attachment object the file is related to"""
        return self._attachment

    @property
    def mode(self) -> str:
        """The mode used to open the file"""
        return self._mode

    @property
    def block_size(self) -> int | None:
        """The block size used to open the file"""
        return self._block_size

    @property
    def cache_options(self) -> dict | None:
        """The cache options used to open the file"""
        return self._cache_options

    @property
    def compression(self) -> str | None:
        """The compression used to open the file"""
        return self._compression

    @property
    def new_version(self) -> bool:
        """Is the file open for a new version"""
        return self._new_version

    @property
    def kwargs(self) -> dict:
        """The kwargs passed when opening the file on the"""
        return self._kwargs

    @property
    def _is_open_for_modify(self) -> bool:
        """Is the file open for modification
        A file is open for modification if it is open for writing or appending
        """
        return "w" in self.mode or "a" in self.mode

    @property
    def _is_open_for_read(self) -> bool:
        """Is the file open for reading"""
        return "r" in self.mode

    @property
    def _is_stored_in_db(self) -> bool:
        """Is the file stored in database"""
        return self.attachment._storage() == "db"

    def __enter__(self) -> io.IOBase:
        """Called when entering the context manager

        Create the file object and return it.
        """
        # we call the attachment instance to get the file object
        self._file_open()
        return self._file

    def _file_open(self) -> io.IOBase:
        """Open the attachment content as a file-like object

        This method will initialize the following attributes:

        * _file: the file-like object.
        * _filesystem: filesystem object.
        * _new_store_fname: the new store_fname if the file is
          opened for a new version.
        """
        new_store_fname = None
        if (
            self._is_open_for_read
            or (self._is_open_for_modify and not self.new_version)
            or self._is_stored_in_db
        ):
            if self.attachment._is_file_from_a_storage(self.attachment.store_fname):
                fs, _storage, fname = self.attachment._get_fs_parts()
                filepath = fname
                filesystem = fs
            elif self.attachment.store_fname:
                filepath = self.attachment._full_path(self.attachment.store_fname)
                filesystem = fsspec.filesystem("file")
            else:
                filepath = f"{self.attachment.id}"
                filesystem = fsspec.filesystem("memory")
                if "a" in self.mode or self._is_open_for_read:
                    filesystem.pipe_file(filepath, self.attachment.db_datas)
            the_file = filesystem.open(
                filepath,
                mode=self.mode,
                block_size=self.block_size,
                cache_options=self.cache_options,
                compression=self.compression,
                **self.kwargs,
            )
        else:
            # mode='w' and new_version=True and storage != 'db'
            # We must create a new file with a new name. If we are in an
            # append mode, we must copy the content of the old file (or create
            # the new one by copy of the old one).
            # to not break the storage plugin mechanism, we'll use the
            # _file_write method to create the new empty file with a random
            # content and checksum to avoid collision.
            content = self._gen_random_content()
            checksum = self.attachment._compute_checksum(content)
            new_store_fname = self.attachment.with_context(
                attachment_res_model=self.attachment.res_model,
                attachment_res_field=self.attachment.res_field,
            )._file_write(content, checksum)
            if self.attachment._is_file_from_a_storage(new_store_fname):
                (
                    filesystem,
                    _storage,
                    new_filepath,
                ) = self.attachment._fs_parse_store_fname(new_store_fname)
                _fs, _storage, old_filepath = self.attachment._get_fs_parts()
            else:
                new_filepath = self.attachment._full_path(new_store_fname)
                old_filepath = self.attachment._full_path(self.attachment.store_fname)
                filesystem = fsspec.filesystem("file")
            if "a" in self.mode:
                filesystem.cp_file(old_filepath, new_filepath)
            the_file = filesystem.open(
                new_filepath,
                mode=self.mode,
                block_size=self.block_size,
                cache_options=self.cache_options,
                compression=self.compression,
                **self.kwargs,
            )
        self._filesystem = filesystem
        self._new_store_fname = new_store_fname
        self._file = the_file

    def _gen_random_content(self, size=256):
        """Generate a random content of size bytes"""
        return os.urandom(size)

    def _file_close(self):
        """Close the file-like object opened by _file_open"""
        if not self._file:
            return
        if not self._file.closed:
            self._file.flush()
            self._file.close()
        if self._is_open_for_modify:
            attachment_data = self._get_attachment_data()
            if (
                not (self.new_version and self._new_store_fname)
                and self._is_stored_in_db
            ):
                attachment_data["raw"] = self._file.getvalue()
            self.attachment.write(attachment_data)
            if self.new_version and self._new_store_fname:
                self.attachment._force_write_store_fname(self._new_store_fname)
            self.attachment._enforce_meaningful_storage_filename()
            self._ensure_cache_consistency()

    def _get_attachment_data(self) -> dict:
        ret = {}
        if self._file:
            file_path = self._file.path
            if hasattr(self._filesystem, "path"):
                file_path = file_path.replace(self._filesystem.path, "")
                file_path = file_path.lstrip("/")
            ret["checksum"] = self._filesystem.checksum(file_path)
            ret["file_size"] = self._filesystem.size(file_path)
            # TODO index_content is too expensive to compute here or should be
            # configurable
            # data = self._file.read()
            # ret["index_content"] = self.attachment._index_content(data,
            #     self.attachment.mimetype, ret["checksum"])
            ret["index_content"] = b""

        return ret

    def _ensure_cache_consistency(self):
        """Ensure the cache consistency once the file is closed"""
        if self._is_open_for_modify and not self._is_stored_in_db:
            self.attachment.invalidate_recordset(fnames=["raw", "datas", "db_datas"])
        if (
            self.attachment.res_model
            and self.attachment.res_id
            and self.attachment.res_field
        ):
            self.attachment.env[self.attachment.res_model].browse(
                self.attachment.res_id
            ).invalidate_recordset(fnames=[self.attachment.res_field])

    def __exit__(self, *args):
        """Called when exiting the context manager.

        Close the file if it is not already closed.
        """
        self._file_close()

    def __getattr__(self, attr):
        """
        Forward all other attributes to the underlying file object.

        This method is required to make the object behave like a file object
        when the AttachmentFileLikeAdapter is used outside a context manager.

        .. code-block:: python

           f = AttachmentFileLikeAdapter(attachment)
           f.read()

        """
        if not self._file:
            self.__enter__()
        return getattr(self._file, attr)
