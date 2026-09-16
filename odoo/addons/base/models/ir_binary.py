import logging
import pathlib
from datetime import UTC, datetime
from mimetypes import guess_extension
from typing import Any

import werkzeug.http

from odoo import _, models
from odoo.exceptions import MissingError, UserError
from odoo.http import Stream, request
from odoo.libs.debug_log import DebugLog
from odoo.libs.filesystem import (
    MIMETYPE_HEAD_SIZE,
    get_extension,
    guess_mimetype,
)
from odoo.tools import file_open, replace_exceptions
from odoo.tools.image import image_guess_size_from_field_name, image_process
from odoo.tools.misc import is_valid_limited_field_access_token

DEFAULT_PLACEHOLDER_PATH = "web/static/img/placeholder.png"
_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class IrBinary(models.AbstractModel):
    _name = "ir.binary"
    _description = "File streaming helper model for controllers"

    def _get_record(
        self,
        xmlid: str | None = None,
        res_model: str = "ir.attachment",
        res_id: int | None = None,
        access_token: str | None = None,
        field_name: str | None = None,
    ) -> Any:
        record = None
        if xmlid:
            record = self.env.ref(xmlid, False)
        elif res_id is not None and res_model in self.env:
            record = self.env[res_model].browse(res_id).exists()
        if not record:
            _debug.logic(
                "record_missing",
                xmlid=xmlid,
                model=res_model,
                res_id=res_id,
                field=field_name,
            )
            raise MissingError(
                _(
                    "No record found for xmlid=%(xmlid)s, res_model=%(model)s, "
                    "id=%(res_id)s",
                    xmlid=xmlid,
                    model=res_model,
                    res_id=res_id,
                )
            )
        if access_token and is_valid_limited_field_access_token(
            record, field_name, access_token, scope="binary"
        ):
            _debug.logic("record_access", model=record._name, via="field_token")
            return record.sudo()
        if record._can_return_content(field_name, access_token):
            _debug.logic("record_access", model=record._name, via="public_or_token")
            return record.sudo()
        record.check_access("read")
        _debug.logic("record_access", model=record._name, via="acl")
        return record

    def _record_to_stream(self, record: Any, field_name: str) -> Stream:
        if record._name == "ir.attachment" and field_name in (
            "raw",
            "datas",
            "db_datas",
        ):
            _debug.logic("record_stream", source="attachment", field=field_name)
            return record._to_http_stream()

        field = record._fields[field_name]
        record._check_field_access(field, "read")

        if field.attachment:
            _debug.logic(
                "record_stream",
                source="field_attachment",
                model=record._name,
                field=field_name,
            )
            field_attachment = (
                self.env["ir.attachment"]
                .sudo()
                .search(
                    domain=[
                        ("res_model", "=", record._name),
                        ("res_id", "=", record.id),
                        ("res_field", "=", field_name),
                    ],
                    limit=1,
                )
            )
            if not field_attachment:
                _debug.logic(
                    "field_attachment_missing", model=record._name, field=field_name
                )
                raise MissingError(self.env._("The related attachment does not exist."))
            return field_attachment._to_http_stream()

        _debug.logic(
            "record_stream", source="column", model=record._name, field=field_name
        )
        return Stream.from_binary_field(record, field_name)

    def _get_stream_from_record(
        self,
        record: Any,
        field_name: str = "raw",
        filename: str | None = None,
        filename_field: str = "name",
        mimetype: str | None = None,
        default_mimetype: str = "application/octet-stream",
    ) -> Stream:
        with replace_exceptions(
            ValueError,
            by=UserError(_("Expected singleton: %(record)s", record=record)),
        ):
            record.check_singleton()

        try:
            field = record._fields[field_name]
        except KeyError:
            _debug.logic(
                "stream_refused",
                model=record._name,
                field=field_name,
                reason="no_field",
            )
            raise UserError(
                _('Record has no field "%(field_name)s".', field_name=field_name)
            ) from None
        if field.type != "binary":
            _debug.logic(
                "stream_refused",
                model=record._name,
                field=field_name,
                reason="not_binary",
                type=field.type,
            )
            raise UserError(
                _(
                    'Field "%(field)s" is type "%(type)s" but it is only possible '
                    "to stream Binary or Image fields.",
                    field=field,
                    type=field.type,
                )
            )

        stream = self._record_to_stream(record, field_name)
        _debug.pipeline(
            "stream_from_record",
            model=record._name,
            field=field_name,
            type=stream.type,
            size=stream.size,
        )

        if stream.type in ("data", "path"):
            if mimetype:
                stream.mimetype = mimetype
            elif not stream.mimetype:
                if stream.type == "data":
                    head = stream.data[:MIMETYPE_HEAD_SIZE]
                else:
                    with pathlib.Path(stream.path).open("rb") as file:
                        head = file.read(MIMETYPE_HEAD_SIZE)
                stream.mimetype = guess_mimetype(head, default=default_mimetype)
                _debug.logic(
                    "stream_mimetype_sniffed",
                    model=record._name,
                    field=field_name,
                    mimetype=stream.mimetype,
                )

            if filename:
                stream.download_name = filename
            elif self._can_name_from_field(record, filename_field):
                stream.download_name = record[filename_field]
            if not stream.download_name:
                stream.download_name = f"{record._table}-{record.id}-{field_name}"

            stream.download_name = stream.download_name.replace("\n", "_").replace(
                "\r", "_"
            )
            ext = get_extension(stream.download_name) or ""
            stream.download_name = stream.download_name.removesuffix(ext)[:100] + ext
            if (
                not get_extension(stream.download_name)
                and stream.mimetype != "application/octet-stream"
            ):
                stream.download_name += guess_extension(stream.mimetype) or ""
            _debug.pipeline(
                "stream_named",
                model=record._name,
                field=field_name,
                mimetype=stream.mimetype,
                named_by="argument" if filename else filename_field,
            )

        return stream

    @staticmethod
    def _can_name_from_field(record: Any, filename_field: str) -> bool:
        name_field = record._fields.get(filename_field)
        if name_field is None or name_field.type != "char":
            return False
        return filename_field == "name" or record.sudo(False)._has_field_access(
            name_field, "read"
        )

    def _get_stream_image_from_record(
        self,
        record: Any,
        field_name: str = "raw",
        filename: str | None = None,
        filename_field: str = "name",
        mimetype: str | None = None,
        default_mimetype: str = "image/png",
        placeholder: str | None = None,
        width: int = 0,
        height: int = 0,
        crop: bool = False,
        quality: int = 0,
    ) -> Stream:
        stream = None
        try:
            stream = self._get_stream_from_record(
                record,
                field_name,
                filename,
                filename_field,
                mimetype,
                default_mimetype,
            )
        except (UserError, MissingError) as exc:
            if request and request.params.get("download"):
                _debug.logic(
                    "image_placeholder_refused",
                    model=record._name,
                    field=field_name,
                    reason="download",
                )
                raise
            _logger.debug(
                "Falling back to the image placeholder for %s.%s: %s",
                record._name,
                field_name,
                exc,
            )

        if not stream or stream.size == 0:
            if not placeholder:
                placeholder = record._get_placeholder_filename(field_name)
            _debug.logic("image_placeholder", model=record._name, field=field_name)
            stream = self._get_stream_placeholder(placeholder)

        if stream.type == "url":
            _debug.logic("image_stream_url", model=record._name, field=field_name)
            return stream
        if not stream.mimetype.startswith("image/"):
            _debug.logic(
                "image_mimetype_rejected",
                model=record._name,
                field=field_name,
                mimetype=stream.mimetype,
            )
            stream.mimetype = "application/octet-stream"

        if (width, height) == (0, 0):
            width, height = image_guess_size_from_field_name(field_name)

        if isinstance(stream.etag, str):
            stream.etag += f"-{width}x{height}-crop={crop}-quality={quality}"

        modified = True
        if request:
            if isinstance(stream.last_modified, (int, float)):
                stream.last_modified = datetime.fromtimestamp(
                    stream.last_modified, tz=UTC
                )
            modified = werkzeug.http.is_resource_modified(
                request.httprequest.environ,
                etag=stream.etag if isinstance(stream.etag, str) else None,
                last_modified=stream.last_modified,
            )
        _debug.logic(
            "image_stream_decided",
            model=record._name,
            field=field_name,
            modified=modified,
            resize=bool(width or height or crop),
            source=stream.type,
        )

        if modified and (width or height or crop):
            if stream.type == "path":
                data = pathlib.Path(stream.path).read_bytes()
                stream.type = "data"
                stream.path = None
                stream.data = data
            with _debug.perf(
                "image_process", size=stream.size, width=width, height=height
            ):
                stream.data = image_process(
                    stream.data,
                    size=(width, height),
                    crop=crop,
                    quality=quality,
                )
            stream.size = len(stream.data)

        return stream

    def _get_stream_placeholder(self, path: str | None = None) -> Stream:
        if not path:
            path = DEFAULT_PLACEHOLDER_PATH
        _debug.logic("placeholder_stream", path=path)
        return Stream.from_path(path, filter_ext=(".png", ".jpg"))

    def _get_placeholder_bytes(self, path: str | bool = False) -> bytes:
        if not path:
            path = DEFAULT_PLACEHOLDER_PATH
        with file_open(path, "rb", filter_ext=(".png", ".jpg")) as file:
            return file.read()
