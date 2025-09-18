import base64
import binascii
import contextlib
import hashlib
import logging
import mimetypes
import re
import uuid
from collections import defaultdict
from itertools import batched
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

import psycopg.errors
import werkzeug

from odoo import _, api, fields, models
from odoo.exceptions import (
    AccessError,
    MissingError,
    UserError,
    ValidationError,
)
from odoo.fields import Domain
from odoo.http import Stream, request, root
from odoo.libs.constants import PREFETCH_MAX
from odoo.libs.filesystem.mimetypes import (
    MIMETYPE_HEAD_SIZE,
    _olecf_mimetypes,
    fix_filename_extension,
    guess_mimetype,
)
from odoo.tools import (
    OrderedSet,
    config,
    consteq,
    human_size,
    image,
    str2bool,
)
from odoo.tools.misc import limited_field_access_token
from odoo.orm._typing import ValuesType

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Generator

    from odoo.tools.query import Query

_logger = logging.getLogger(__name__)
SECURITY_FIELDS = ("res_model", "res_id", "create_uid", "public", "res_field")


def condition_values(model: Any, field_name: str, domain: Domain) -> list[Any] | None:
    """Get the values in the domain for a specific field name.

    Returns the values appearing in the `in` conditions that would be restricted
    to by the domain.
    """
    domain = domain.optimize(model)
    for condition in (
        domain.map_conditions(
            lambda cond: (
                cond
                if cond.field_expr == field_name and cond.operator == "in"
                else Domain.TRUE
            )
        )
        .optimize(model)
        .iter_conditions()
    ):
        return condition.value
    return None


class IrAttachment(models.Model):
    """Attachments are used to link binary files or url to any Odoo document.

    External attachment storage
    ---------------------------

    The computed field ``datas`` is implemented using ``_file_read``,
    ``_file_write`` and ``_file_delete``, which can be overridden to implement
    other storage engines. Such methods should check for other location pseudo
    uri (example: hdfs://hadoopserver).

    The default implementation is the file:dirname location that stores files
    on the local filesystem using name based on their sha1 hash
    """

    _name = "ir.attachment"
    _description = "Attachment"
    _order = "id desc"

    def _compute_res_name(self) -> None:
        to_compute = self.filtered(lambda a: a.res_model and a.res_id)
        (self - to_compute).res_name = False
        for res_model, attachments in to_compute.grouped("res_model").items():
            res_ids = attachments.mapped("res_id")
            records = self.env[res_model].browse(res_ids)
            name_map = {record.id: record.display_name for record in records}
            for attachment in attachments:
                attachment.res_name = name_map.get(attachment.res_id, False)

    @api.model
    def _storage(self) -> str:
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("ir_attachment.location", "file")
        )

    @api.model
    def _filestore(self) -> str:
        return config.filestore(self.env.cr.dbname)

    @api.model
    def _get_storage_domain(self) -> list[tuple[str, str, Any]]:
        # domain to retrieve the attachments to migrate
        return {
            "db": [("store_fname", "!=", False)],
            "file": [("db_datas", "!=", False)],
        }[self._storage()]

    @api.model
    def force_storage(self) -> None:
        """Force all attachments to be stored in the currently configured storage"""
        if not self.env.is_admin():
            raise AccessError(_("Only administrators can execute this action."))

        # Migrate only binary attachments and bypass the res_field automatic
        # filter added in _search override
        self.search(
            Domain.AND(
                [
                    self._get_storage_domain(),
                    [
                        "&",
                        ("type", "=", "binary"),
                        "|",
                        ("res_field", "=", False),
                        ("res_field", "!=", False),
                    ],
                ]
            )
        )._migrate()

    def _migrate(self) -> None:
        record_count = len(self)
        storage = self._storage().upper()
        for index, attach in enumerate(self):
            _logger.debug(
                "Migrate attachment %s/%s to %s",
                index + 1,
                record_count,
                storage,
            )
            # pass mimetype, to avoid recomputation
            attach.write({"raw": attach.raw, "mimetype": attach.mimetype})

    @api.model
    def _full_path(self, path: str) -> str:
        # sanitize path
        path = re.sub(r"[.:]", "", path)
        path = path.strip("/\\")
        filestore = Path(self._filestore()).resolve()
        full = (filestore / path).resolve()
        # Ensure the resolved path is within the filestore (defense-in-depth).
        # Use is_relative_to() for proper path-component checking — str.startswith()
        # would incorrectly accept sibling dirs like /data/odoo-evil for /data/odoo.
        if not full.is_relative_to(filestore):
            raise ValueError(f"Attachment path {path!r} escapes the filestore")
        return str(full)

    @api.model
    def _get_path(self, bin_data: bytes, sha: str) -> tuple[str, str]:
        # scatter files across 256 dirs
        # we use '/' in the db (even on windows)
        fname = sha[:2] + "/" + sha
        full_path = self._full_path(fname)
        dirname = str(Path(full_path).parent)
        if not Path(dirname).is_dir():
            Path(dirname).mkdir(exist_ok=True, parents=True)

        # prevent sha-1 collision
        if Path(full_path).is_file() and not self._same_content(bin_data, full_path):
            raise UserError(_("The attachment collides with an existing file."))
        return fname, full_path

    @api.model
    def _file_read(self, fname: str, size: int | None = None) -> bytes:
        assert isinstance(self, IrAttachment)
        full_path = self._full_path(fname)
        try:
            with Path(full_path).open("rb") as f:
                return f.read(size)
        except OSError:
            _logger.info("_read_file reading %s", full_path, exc_info=True)
        return b""

    @api.model
    def _file_write(self, bin_value: bytes, checksum: str) -> str:
        assert isinstance(self, IrAttachment)
        fname, full_path = self._get_path(bin_value, checksum)
        if not Path(full_path).exists():
            try:
                with Path(full_path).open("wb") as fp:
                    fp.write(bin_value)
                # add fname to checklist, in case the transaction aborts
                self._mark_for_gc(fname)
            except OSError:
                _logger.info("_file_write writing %s", full_path)
                raise
        return fname

    @api.model
    def _file_delete(self, fname: str) -> None:
        # simply add fname to checklist, it will be garbage-collected later
        self._mark_for_gc(fname)

    def _mark_for_gc(self, fname: str) -> None:
        """Add ``fname`` in a checklist for the filestore garbage collection."""
        assert isinstance(self, IrAttachment)
        fname = re.sub(r"[.:]", "", fname).strip("/\\")
        # we use a spooldir: add an empty file in the subdirectory 'checklist'
        full_path = str(Path(self._full_path("checklist"), fname))
        if not Path(full_path).exists():
            dirname = str(Path(full_path).parent)
            if not Path(dirname).is_dir():
                with contextlib.suppress(OSError):
                    Path(dirname).mkdir(parents=True)
            with Path(full_path).open("ab"):
                pass

    @api.autovacuum
    def _gc_file_store(self) -> None | bool:
        """Perform the garbage collection of the filestore."""
        assert isinstance(self, IrAttachment)
        if self._storage() != "file":
            return None

        # Continue in a new transaction. The LOCK statement below must be the
        # first one in the current transaction, otherwise the database snapshot
        # used by it may not contain the most recent changes made to the table
        # ir_attachment! Indeed, if concurrent transactions create attachments,
        # the LOCK statement will wait until those concurrent transactions end.
        # But this transaction will not see the new attachements if it has done
        # other requests before the LOCK (like the method _storage() above).
        cr = self.env.cr
        cr.commit()

        # prevent all concurrent updates on ir_attachment while collecting,
        # but only attempt to grab the lock for a little bit, otherwise it'd
        # start blocking other transactions. (will be retried later anyway)
        cr.execute("SET LOCAL lock_timeout TO '10s'")
        try:
            cr.execute("LOCK ir_attachment IN SHARE MODE")
        except psycopg.errors.LockNotAvailable:
            cr.rollback()
            return False

        self._gc_file_store_unsafe()

        # commit to release the lock
        cr.commit()
        return None

    def _gc_file_store_unsafe(self) -> None:
        # retrieve the file names from the checklist
        checklist = {}
        checklist_root = Path(self._full_path("checklist"))
        for dirpath, _subdirs, filenames in checklist_root.walk():
            for filename in filenames:
                # Use relative_to() so fname is correct regardless of nesting depth.
                # dirpath.name would only work for a 2-level structure.
                fname = str((dirpath / filename).relative_to(checklist_root))
                checklist[fname] = dirpath / filename

        # Clean up the checklist. The checklist is split in chunks and files are garbage-collected
        # for each chunk.
        removed = 0
        for names in batched(checklist, self.env.cr.BATCH_SIZE, strict=False):
            # determine which files to keep among the checklist
            self.env.cr.execute(
                "SELECT store_fname FROM ir_attachment WHERE store_fname = ANY(%s)",
                [list(names)],
            )
            whitelist = {row[0] for row in self.env.cr.fetchall()}

            # remove garbage files, and clean up checklist
            for fname in names:
                filepath = checklist[fname]
                if fname not in whitelist:
                    full_path = self._full_path(fname)
                    try:
                        Path(full_path).unlink()
                        _logger.debug("_file_gc unlinked %s", full_path)
                        removed += 1
                    except OSError:
                        _logger.info(
                            "_file_gc could not unlink %s",
                            full_path,
                            exc_info=True,
                        )
                        # Keep the checklist entry so the file is retried on
                        # the next GC run instead of being permanently orphaned.
                        continue
                with contextlib.suppress(OSError):
                    Path(filepath).unlink()

        _logger.info("filestore gc %d checked, %d removed", len(checklist), removed)

    @api.depends("store_fname", "db_datas", "file_size")
    @api.depends_context("bin_size")
    def _compute_datas(self) -> None:
        if self.env.context.get("bin_size"):
            for attach in self:
                attach.datas = human_size(attach.file_size)
            return

        for attach in self:
            attach.datas = base64.b64encode(attach.raw or b"")

    @api.depends("store_fname", "db_datas")
    def _compute_raw(self) -> None:
        for attach in self:
            if attach.store_fname:
                attach.raw = attach._file_read(attach.store_fname)
            else:
                attach.raw = attach.db_datas

    def _inverse_raw(self) -> None:
        self._set_attachment_data(lambda a: a.raw or b"")

    def _inverse_datas(self) -> None:
        self._set_attachment_data(lambda attach: base64.b64decode(attach.datas or b""))

    def _set_attachment_data(self, asbytes: Callable[[Any], bytes]) -> None:
        old_fnames = []
        checksum_raw_map = {}
        use_filestore = self._storage() != "db"

        for attach in self:
            # compute the fields that depend on datas
            bin_data = asbytes(attach)
            vals = self._get_datas_related_values(
                bin_data, attach.mimetype, use_filestore=use_filestore
            )
            if bin_data:
                checksum_raw_map[vals["checksum"]] = bin_data

            # take current location in filestore to possibly garbage-collect it
            if attach.store_fname:
                old_fnames.append(attach.store_fname)

            # write as superuser, as user probably does not have write access
            super(IrAttachment, attach.sudo()).write(vals)

        if use_filestore:
            # before touching the filestore, flush to prevent the GC from
            # running until the end of the transaction
            self.flush_recordset(["checksum", "store_fname"])
            for fname in old_fnames:
                self._file_delete(fname)
            for checksum, raw in checksum_raw_map.items():
                self._file_write(raw, checksum)

    def _get_datas_related_values(
        self, data: bytes, mimetype: str, *, use_filestore: bool | None = None
    ) -> dict[str, Any]:
        checksum = self._compute_checksum(data)
        try:
            index_content = self._index(data, mimetype, checksum=checksum)
        except TypeError:
            index_content = self._index(data, mimetype)
        values = {
            "file_size": len(data),
            "checksum": checksum,
            "index_content": index_content,
            "store_fname": False,
            "db_datas": data,
        }
        if use_filestore is None:
            use_filestore = self._storage() != "db"
        if data and use_filestore:
            values["store_fname"], _full_path = self._get_path(data, checksum)
            values["db_datas"] = False
        return values

    def _compute_checksum(self, bin_data: bytes) -> str:
        """compute the checksum for the given datas
        :param bin_data : datas in its binary form
        """
        # an empty file has a checksum too (for caching)
        return hashlib.sha1(bin_data or b"").hexdigest()

    @api.model
    def _same_content(self, bin_data: bytes, filepath: str) -> bool:
        BLOCK_SIZE = 1024
        with Path(filepath).open("rb") as fd:
            i = 0
            while True:
                data = fd.read(BLOCK_SIZE)
                if data != bin_data[i * BLOCK_SIZE : (i + 1) * BLOCK_SIZE]:
                    return False
                if not data:
                    break
                i += 1
        return True

    def _compute_mimetype(self, values: dict[str, Any]) -> str:
        """compute the mimetype of the given values
        :param values : dict of values to create or write an ir_attachment
        :return mime : string indicating the mimetype, or application/octet-stream by default
        """
        mimetype = None
        if values.get("mimetype"):
            mimetype = values["mimetype"]
        if not mimetype and values.get("name"):
            mimetype = mimetypes.guess_type(values["name"])[0]
        if not mimetype and values.get("url"):
            mimetype = mimetypes.guess_type(values["url"].split("?")[0])[0]
        if not mimetype or mimetype == "application/octet-stream":
            raw = None
            if "raw" in values and values["raw"] is not None:
                raw = values["raw"]
            elif values.get("datas"):
                raw = base64.b64decode(values["datas"])
            if raw:
                mimetype = guess_mimetype(raw)
        return (mimetype and mimetype.lower()) or "application/octet-stream"

    def _postprocess_contents(self, values: dict[str, Any]) -> dict[str, Any]:
        ICP = self.env["ir.config_parameter"].sudo().get_param
        supported_subtype = ICP(
            "base.image_autoresize_extensions", "png,jpeg,bmp,tiff"
        ).split(",")

        mimetype = values["mimetype"] = self._compute_mimetype(values)
        _type, _match, _subtype = mimetype.partition("/")
        is_image_resizable = _type == "image" and _subtype in supported_subtype
        if is_image_resizable and (values.get("datas") or values.get("raw")):
            is_raw = values.get("raw")

            # Can be set to 0 to skip the resize
            max_resolution = ICP("base.image_autoresize_max_px", "1920x1920")
            if str2bool(max_resolution, True):
                try:
                    if is_raw:
                        img = image.ImageProcess(values["raw"], verify_resolution=False)
                    else:  # datas
                        img = image.ImageProcess(
                            base64.b64decode(values["datas"]),
                            verify_resolution=False,
                        )

                    if not img.image:
                        _logger.info(
                            "Post processing ignored : Empty source, SVG, or WEBP"
                        )
                        return values

                    w, h = img.image.size
                    nw, nh = map(int, max_resolution.split("x"))
                    if w > nw or h > nh:
                        img = img.resize(nw, nh)
                        if _subtype == "jpeg":  # Do not affect PNGs color palette
                            quality = int(ICP("base.image_autoresize_quality", 80))
                        else:
                            quality = 0
                        image_data = img.image_quality(quality=quality)
                        if is_raw:
                            values["raw"] = image_data
                        else:
                            values["datas"] = base64.b64encode(image_data)
                except UserError as e:
                    # Catch error during test where we provide fake image
                    msg = str(
                        e
                    )  # the exception can be lazy-translated, resolve it here
                    _logger.info("Post processing ignored : %s", msg)
        return values

    def _check_contents(self, values: dict[str, Any]) -> dict[str, Any]:
        mimetype = values["mimetype"] = self._compute_mimetype(values)
        xml_like = "ht" in mimetype or (  # hta, html, xhtml, etc.
            "xml" in mimetype  # other xml (svg, text/xml, etc)
            and not mimetype.startswith("application/vnd.openxmlformats")
        )  # exception for Office formats
        force_text = xml_like and (
            self.env.context.get("attachments_mime_plainxml")
            or not self.env["ir.ui.view"].sudo(False).has_access("write")
        )
        if force_text:
            values["mimetype"] = "text/plain"
        if not self.env.context.get("image_no_postprocess"):
            values = self._postprocess_contents(values)
        return values

    @api.model
    def _index(
        self, bin_data: bytes, file_type: str, checksum: str | None = None
    ) -> str | None:
        """compute the index content of the given binary data.
        This is a python implementation of the unix command 'strings'.
        """
        # compute index_content only for text type
        if file_type and file_type.startswith("text/"):
            words = re.findall(rb"[\x20-\x7E]{4,}", bin_data)
            return b"\n".join(words).decode("ascii")
        return None

    @api.model
    def get_serving_groups(self) -> list[str]:
        """An ir.attachment record may be used as a fallback in the
        http dispatch if its type field is set to "binary" and its url
        field is set as the request's url. Only the groups returned by
        this method are allowed to create and write on such records.
        """
        return ["base.group_system"]

    name = fields.Char("Name", required=True)
    description = fields.Text("Description")
    res_name = fields.Char("Resource Name", compute="_compute_res_name")
    res_model = fields.Char("Resource Model")
    res_field = fields.Char("Resource Field")
    res_id = fields.Many2oneReference("Resource ID", model_field="res_model")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        change_default=True,
        default=lambda self: self.env.company,
    )
    type = fields.Selection(
        [("url", "URL"), ("binary", "File")],
        string="Type",
        required=True,
        default="binary",
        change_default=True,
        help="You can either upload a file from your computer or copy/paste an internet link to your file.",
    )
    url = fields.Char("Url", index="btree_not_null", size=1024)
    public = fields.Boolean("Is public document")

    # for external access
    access_token = fields.Char("Access Token", groups="base.group_user")

    # the field 'datas' is computed and may use the other fields below
    raw = fields.Binary(
        string="File Content (raw)",
        compute="_compute_raw",
        inverse="_inverse_raw",
    )
    datas = fields.Binary(
        string="File Content (base64)",
        compute="_compute_datas",
        inverse="_inverse_datas",
    )
    db_datas = fields.Binary("Database Data", attachment=False)
    store_fname = fields.Char("Stored Filename", index=True)
    file_size = fields.Integer("File Size", readonly=True)
    checksum = fields.Char("Checksum/SHA1", size=40, readonly=True)
    mimetype = fields.Char("Mime Type", readonly=True)
    index_content = fields.Text("Indexed Content", readonly=True, prefetch=False)

    _res_idx = models.Index("(res_model, res_id)")

    def _check_serving_attachments(self) -> None:
        if self.env.is_admin():
            return
        for attachment in self:
            # restrict writing on attachments that could be served by the
            # ir.http's dispatch exception handling
            # XDO note: if read on sudo, read twice, one for constraints, one for _inverse_datas as user
            if attachment.type == "binary" and attachment.url:
                has_group = self.env.user.has_group
                if not any(has_group(g) for g in attachment.get_serving_groups()):
                    raise ValidationError(
                        _("Sorry, you are not allowed to write on this document")
                    )

    def _check_access(self, operation: str) -> tuple[Self, Callable] | None:
        """Check access for attachments.

        Rules:
        - `public` is always accessible for reading.
        - If we have `res_model and res_id`, the attachment is accessible if the
          referenced model is accessible. Also, when `res_field != False` and
          the user is not an administrator, we check the access on the field.
        - If we don't have a referenced record, the attachment is accessible to
          the administrator and the creator of the attachment.
        """
        res = super()._check_access(operation)
        remaining = self
        error_func = None
        forbidden_ids = OrderedSet()
        if res:
            forbidden, error_func = res
            if forbidden == self:
                return res
            remaining -= forbidden
            forbidden_ids.update(forbidden._ids)
        elif not self:
            return None

        if operation in ("create", "unlink"):
            # check write operation instead of unlinking and creating for
            # related models and field access
            operation = "write"

        # collect the records to check (by model)
        model_ids = defaultdict(set)  # {model_name: set(ids)}
        att_model_ids = []  # [(att_id, (res_model, res_id))]
        # DLE P173: `test_01_portal_attachment`
        remaining = remaining.sudo()
        remaining.fetch(SECURITY_FIELDS)  # fetch only these fields
        for attachment in remaining:
            if attachment.public and operation == "read":
                continue
            att_id = attachment.id
            res_model, res_id = attachment.res_model, attachment.res_id
            if not self.env.is_system():
                if not res_id and attachment.create_uid.id != self.env.uid:
                    forbidden_ids.add(att_id)
                    continue
                if res_field := attachment.res_field:
                    try:
                        field = self.env[res_model]._fields[res_field]
                    except KeyError:
                        # field does not exist
                        field = None
                    if field is None or not self._has_field_access(field, operation):
                        forbidden_ids.add(att_id)
                        continue
            if res_model and res_id:
                model_ids[res_model].add(res_id)
                att_model_ids.append((att_id, (res_model, res_id)))
        forbidden_res_model_id = set(
            self._inaccessible_comodel_records(model_ids, operation)
        )
        forbidden_ids.update(
            att_id for att_id, res in att_model_ids if res in forbidden_res_model_id
        )

        if forbidden_ids:
            forbidden = self.browse(forbidden_ids)
            forbidden.invalidate_recordset(SECURITY_FIELDS)  # avoid cache pollution
            if error_func is None:

                def error_func():
                    return AccessError(
                        self.env._(
                            "Sorry, you are not allowed to access this document. "
                            "Please contact your system administrator.\n\n"
                            "(Operation: %(operation)s)\n\n"
                            "Records: %(records)s, User: %(user)s",
                            operation=operation,
                            records=forbidden[:6],
                            user=self.env.uid,
                        )
                    )

            return forbidden, error_func
        return None

    def _inaccessible_comodel_records(
        self, model_and_ids: dict[str, Collection[int]], operation: str
    ) -> Generator[tuple[str, int]]:
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
            if (
                res_model == "res.users"
                and len(records) == 1
                and self.env.uid == records.id
            ):
                # by default a user cannot write on itself, despite the list of writable fields
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
    def _search(
        self,
        domain: Any,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
        *,
        active_test: bool = True,
        bypass_access: bool = False,
    ) -> Query:
        assert not self._active_name, "active name not supported on ir.attachment"
        disable_binary_fields_attachments = False
        domain = Domain(domain)
        if (
            not self.env.context.get("skip_res_field_check")
            and not any(
                d.field_expr in ("id", "res_field") for d in domain.iter_conditions()
            )
            and not bypass_access
        ):
            disable_binary_fields_attachments = True
            domain &= Domain("res_field", "=", False)

        domain = domain.optimize(self)
        if self.env.su or bypass_access or domain.is_false():
            return super()._search(
                domain,
                offset,
                limit,
                order,
                active_test=active_test,
                bypass_access=bypass_access,
            )

        # General access rules
        # - public == True are always accessible
        sec_domain = Domain("public", "=", True)
        # - res_id == False needs to be system user or creator
        res_ids = condition_values(self, "res_id", domain)
        if not res_ids or False in res_ids:
            if self.env.is_system():
                sec_domain |= Domain("res_id", "=", False)
            else:
                sec_domain |= Domain("res_id", "=", False) & Domain(
                    "create_uid", "=", self.env.uid
                )

        # Search by res_model and res_id, filter using permissions from res_model
        # - res_id != False needs then check access on the linked res_model record
        # - res_field != False needs to check field access on the res_model
        res_model_names = condition_values(self, "res_model", domain)
        if 0 < len(res_model_names or ()) <= 5:
            env = self.with_context(active_test=False).env
            for res_model_name in res_model_names:
                if (comodel := env.get(res_model_name)) is None:
                    continue
                codomain = Domain("res_model", "=", comodel._name)
                comodel_res_ids = condition_values(
                    self,
                    "res_id",
                    domain.map_conditions(
                        lambda cond, codomain=codomain: (
                            codomain & cond if cond.field_expr == "res_model" else cond
                        )
                    ),
                )
                query = comodel._search(
                    Domain("id", "in", comodel_res_ids)
                    if comodel_res_ids
                    else Domain.TRUE
                )
                if query.is_empty():
                    continue
                if query.where_clause:
                    codomain &= Domain("res_id", "in", query)
                if not disable_binary_fields_attachments and not self.env.is_system():
                    accessible_fields = [
                        field.name
                        for field in comodel._fields.values()
                        if field.type == "binary"
                        or (field.relational and field.comodel_name == self._name)
                        if comodel._has_field_access(field, "read")
                    ]
                    accessible_fields.append(False)
                    codomain &= Domain("res_field", "in", accessible_fields)
                sec_domain |= codomain

            return super()._search(
                domain & sec_domain,
                offset,
                limit,
                order,
                active_test=active_test,
            )

        # We do not have a small restriction on res_model. We still need to
        # support other queries such as: `('id', 'in' ...)`.
        # Restrict with domain and add all attachments linked to a model.
        domain &= sec_domain | Domain("res_model", "!=", False)
        domain = domain.optimize_full(self)
        ordered = bool(order)
        if limit is None:
            records = (
                self.sudo()
                .with_context(active_test=False)
                .search_fetch(domain, SECURITY_FIELDS, order=order)
                .sudo(False)
            )
            return records._filtered_access("read")[offset:]._as_query(ordered)
        # Fetch by small batches
        sub_offset = 0
        limit += offset
        result = []
        if not ordered:
            # By default, order by model to batch access checks.
            order = "res_model nulls first, id"
        while len(result) < limit:
            records = (
                self.sudo()
                .with_context(active_test=False)
                .search_fetch(
                    domain,
                    SECURITY_FIELDS,
                    offset=sub_offset,
                    limit=PREFETCH_MAX,
                    order=order,
                )
                .sudo(False)
            )
            result.extend(records._filtered_access("read")._ids)
            if len(records) < PREFETCH_MAX:
                # There are no more records
                break
            sub_offset += PREFETCH_MAX
        return self.browse(result[offset:limit])._as_query(ordered)

    def write(self, vals: dict[str, Any]) -> bool:
        self.check_access("write")
        if "res_model" in vals or "res_id" in vals:
            model_and_ids = defaultdict(OrderedSet)
            if "res_model" in vals and "res_id" in vals:
                model_and_ids[vals["res_model"]].add(vals["res_id"])
            else:
                for record in self:
                    model_and_ids[vals.get("res_model", record.res_model)].add(
                        vals.get("res_id", record.res_id)
                    )
            if any(self._inaccessible_comodel_records(model_and_ids, "write")):
                raise AccessError(
                    _("Sorry, you are not allowed to access this document.")
                )
        # remove computed field depending of datas
        for field in ("file_size", "checksum", "store_fname"):
            vals.pop(field, False)
        if "mimetype" in vals or "datas" in vals or "raw" in vals:
            vals = self._check_contents(vals)
        res = super().write(vals)
        if "url" in vals or "type" in vals:
            self._check_serving_attachments()
        return res

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for attachment, vals in zip(self, vals_list, strict=True):
            if not default.keys() & {"datas", "db_datas", "raw"}:
                # ensure the content is kept and recomputes checksum/store_fname
                vals["raw"] = attachment.raw
        return vals_list

    def unlink(self) -> bool:
        # First delete in the database, *then* in the filesystem if the
        # database allowed it. Helps avoid errors when concurrent transactions
        # are deleting the same file, and some of the transactions are
        # rolled back by PostgreSQL (due to concurrent updates detection).
        to_delete = OrderedSet(
            attach.store_fname for attach in self if attach.store_fname
        )
        res = super().unlink()
        for file_path in to_delete:
            self._file_delete(file_path)

        return res

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        record_tuple_set = set()

        # remove computed field depending of datas
        vals_list = [
            {
                key: value
                for key, value in vals.items()
                if key not in ("file_size", "checksum", "store_fname")
            }
            for vals in vals_list
        ]
        checksum_raw_map = {}

        for values in vals_list:
            # needs to be popped in all cases to bypass `_inverse_datas`
            datas = values.pop("datas", None)
            if raw := values.get("raw"):
                if isinstance(raw, str):
                    values["raw"] = raw.encode()
            elif datas:
                values["raw"] = base64.b64decode(datas)
            else:
                values["raw"] = b""

            values = self._check_contents(values)
            # pop() must always run to prevent _inverse_datas from re-processing;
            # separate it from the condition to make the side-effect explicit.
            raw = values.pop("raw")
            if raw:
                values.update(self._get_datas_related_values(raw, values["mimetype"]))
                checksum_raw_map[values["checksum"]] = raw

            # 'check()' only uses res_model and res_id from values, and make an exists.
            # We can group the values by model, res_id to make only one query when
            # creating multiple attachments on a single record.
            record_tuple = (values.get("res_model"), values.get("res_id"))
            record_tuple_set.add(record_tuple)

        # don't use possible contextual recordset for check, see commit for details
        model_and_ids = defaultdict(set)
        for res_model, res_id in record_tuple_set:
            model_and_ids[res_model].add(res_id)
        if any(self._inaccessible_comodel_records(model_and_ids, "write")):
            raise AccessError(_("Sorry, you are not allowed to access this document."))
        records = super().create(vals_list)
        if self._storage() != "db":
            for checksum, raw in checksum_raw_map.items():
                self._file_write(raw, checksum)
        records._check_serving_attachments()
        return records

    def _post_add_create(self, **kwargs: Any) -> None:
        """Hook called after an attachment is uploaded. Overridden by mail, account, etc."""

    def generate_access_token(self) -> list[str]:
        tokens = []
        for attachment in self:
            if attachment.access_token:
                tokens.append(attachment.access_token)
                continue
            access_token = self._generate_access_token()
            attachment.write({"access_token": access_token})
            tokens.append(access_token)
        return tokens

    def _get_raw_access_token(self) -> str:
        """Return a scoped access token for the `raw` field. The token can be
        used with `ir_binary._find_record` to bypass access rights.

        :rtype: str
        """
        self.ensure_one()
        return limited_field_access_token(self, "raw", scope="binary")

    @api.model
    def create_unique(self, values_list: list[dict[str, Any]]) -> list[int]:
        ids = []
        for values in values_list:
            # Create only if record does not already exist for checksum and size.
            try:
                bin_data = base64.b64decode(values.get("datas", ""))
            except binascii.Error:
                raise UserError(_("Attachment is not encoded in base64."))
            checksum = self._compute_checksum(bin_data)
            existing_domain = [
                ["id", "!=", False],  # No implicit condition on res_field.
                ["checksum", "=", checksum],
                ["file_size", "=", len(bin_data)],
                ["mimetype", "=", values["mimetype"]],
            ]
            if existing := self.sudo().search(existing_domain, limit=1):
                ids.append(existing.id)
            else:
                attachment = self.create(values)
                ids.append(attachment.id)
        return ids

    def _generate_access_token(self) -> str:
        return str(uuid.uuid4())

    @api.model
    def action_get(self) -> dict[str, Any]:
        return self.env["ir.actions.act_window"]._for_xml_id("base.action_attachment")

    @api.model
    def _get_serve_attachment(
        self, url: str, extra_domain: Any = None, order: str | None = None
    ) -> Self:
        domain = (
            Domain("type", "=", "binary")
            & Domain("url", "=", url)
            & Domain(extra_domain or [])
        )
        return self.search(domain, order=order, limit=1)

    @api.model
    def regenerate_assets_bundles(self) -> None:
        self.search(
            [
                ("public", "=", True),
                ("url", "=like", "/web/assets/%"),
                ("res_model", "=", "ir.ui.view"),
                ("res_id", "=", 0),
                ("create_uid", "=", api.SUPERUSER_ID),
            ]
        ).unlink()
        self.env.registry.clear_cache("assets")

    def _from_request_file(self, file: Any, *, mimetype: str, **vals: Any) -> Self:
        """
        Create an attachment out of a request file

        :param file: the request file
        :param str mimetype:
            * "TRUST" to use the mimetype and file extension from the
              request file with no verification.
            * "GUESS" to determine the mimetype and file extension on
              the file's content. The determined extension is added at
              the end of the filename unless the filename already had a
              valid extension.
            * a mimetype in format "{type}/{subtype}" to force the
              mimetype to the given value, it adds the corresponding
              file extension at the end of the filename unless the
              filename already had a valid extension.
        """
        if mimetype == "TRUST":
            mimetype = file.content_type
            filename = file.filename
        elif mimetype == "GUESS":
            head = file.read(MIMETYPE_HEAD_SIZE)
            file.seek(-len(head), 1)  # rewind
            mimetype = guess_mimetype(head)
            filename = fix_filename_extension(file.filename, mimetype)
            if mimetype in ("application/zip", *_olecf_mimetypes):
                mimetype = mimetypes.guess_type(filename)[0]
        elif all(mimetype.partition("/")):
            filename = fix_filename_extension(file.filename, mimetype)
        else:
            raise ValueError(f"{mimetype=}")

        return self.create(
            {
                "name": filename,
                "type": "binary",
                "raw": file.read(),  # load the entire file in memory :(
                "mimetype": mimetype,
                **vals,
            }
        )

    def _to_http_stream(self) -> Stream:
        """Create a :class:`~Stream`: from an ir.attachment record."""
        self.ensure_one()

        stream = Stream(
            mimetype=self.mimetype,
            download_name=self.name,
            etag=self.checksum,
            public=self.public,
        )

        if self.store_fname:
            stream.type = "path"
            stream.path = werkzeug.security.safe_join(
                str(Path(config.filestore(request.db)).resolve()),
                self.store_fname,
            )
            stat = Path(stream.path).stat()
            stream.last_modified = stat.st_mtime
            stream.size = stat.st_size

        elif self.db_datas:
            stream.type = "data"
            stream.data = self.raw
            stream.last_modified = self.write_date
            stream.size = len(stream.data)

        elif self.url:
            # When the URL targets a file located in an addon, assume it
            # is a path to the resource. It saves an indirection and
            # stream the file right away.
            static_path = root.get_static_file(
                self.url, host=request.httprequest.environ.get("HTTP_HOST", "")
            )
            if static_path:
                stream = Stream.from_path(static_path, public=True)
            else:
                stream.type = "url"
                stream.url = self.url

        else:
            stream.type = "data"
            stream.data = b""
            stream.size = 0

        return stream

    def _is_remote_source(self) -> bool:
        self.ensure_one()
        return (
            self.url
            and not self.file_size
            and self.url.startswith(("http://", "https://", "ftp://"))
        )

    def _can_return_content(
        self, field_name: str | None = None, access_token: str | None = None
    ) -> bool:
        attachment_sudo = self.sudo().with_context(prefetch_fields=False)
        if access_token:
            if not consteq(attachment_sudo.access_token or "", access_token):
                msg = "Invalid access token"
                raise AccessError(msg)  # pylint: disable=missing-gettext,E8507
            return True
        if attachment_sudo.public:
            return True
        if self.env.user._is_portal():
            # Check the read access on the record linked to the attachment
            # eg: Allow to download an attachment on a task from /my/tasks/task_id
            self.check_access("read")
            return True
        return super()._can_return_content(field_name, access_token)

    def _migrate_remote_to_local(self) -> None:
        if self.type == "binary":
            return
        if self.type == "url":
            raise ValidationError(
                _(
                    "URL attachment (%s) shouldn't be migrated to local.",
                    self.id,
                )
            )
