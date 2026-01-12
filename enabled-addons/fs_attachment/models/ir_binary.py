# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

import werkzeug.http

from odoo import models
from odoo.http import request
from odoo.tools.image import image_process

from ..fs_stream import FsStream

_logger = logging.getLogger(__name__)


class IrBinary(models.AbstractModel):
    _inherit = "ir.binary"

    def _get_fs_attachment_for_field(self, record, field_name):
        if record._name == "ir.attachment" and record.fs_filename:
            return record

        record.check_field_access_rights("read", [field_name])
        field_def = record._fields[field_name]
        if field_def.attachment and field_def.store:
            fs_attachment = (
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
            if fs_attachment and fs_attachment.fs_filename:
                return fs_attachment
        return None

    def _record_to_stream(self, record, field_name):
        # Extend base implementation to support attachment stored into a
        # filesystem storage
        fs_attachment = self._get_fs_attachment_for_field(record, field_name)
        if fs_attachment:
            return FsStream.from_fs_attachment(fs_attachment)
        return super()._record_to_stream(record, field_name)

    def _get_stream_from(
        self,
        record,
        field_name="raw",
        filename=None,
        filename_field="name",
        mimetype=None,
        default_mimetype="application/octet-stream",
    ):
        stream = super()._get_stream_from(
            record,
            field_name=field_name,
            filename=filename,
            filename_field=filename_field,
            mimetype=mimetype,
            default_mimetype=default_mimetype,
        )

        if stream.type == "fs":
            if mimetype:
                stream.mimetype = mimetype
            if filename:
                stream.download_name = filename
            elif record and filename_field in record:
                stream.download_name = record[filename_field] or stream.download_name

        return stream

    def _get_image_stream_from(
        self,
        record,
        field_name="raw",
        filename=None,
        filename_field="name",
        mimetype=None,
        default_mimetype="image/png",
        placeholder=None,
        width=0,
        height=0,
        crop=False,
        quality=0,
    ):
        # we need to override this method since if you pass a width or height or
        # set crop=True, the stream data must be a bytes object, not a
        # file-like object. In the base implementation, the stream data is
        # passed to `image_process` method to transform it and this method
        # expects a bytes object.
        initial_width = width
        initial_height = height
        initial_crop = crop
        if record._name != "ir.attachment" and field_name:
            field_def = record._fields[field_name]
            if field_def.type in ("fs_image", "fs_file"):
                value = record[field_name]
                if value:
                    record = value.attachment
                    field_name = "raw"
            elif field_def.type in ("binary"):
                fs_attachment = self._get_fs_attachment_for_field(record, field_name)
                if fs_attachment:
                    record = fs_attachment
                    field_name = "raw"
        stream = super()._get_image_stream_from(
            record,
            field_name=field_name,
            filename=filename,
            filename_field=filename_field,
            mimetype=mimetype,
            default_mimetype=default_mimetype,
            placeholder=placeholder,
            width=0,
            height=0,
            crop=False,
            quality=quality,
        )
        modified = werkzeug.http.is_resource_modified(
            request.httprequest.environ,
            etag=stream.etag,
            last_modified=stream.last_modified,
        )
        if modified and (initial_width or initial_height or initial_crop):
            if stream.type == "path":
                with open(stream.path, "rb") as file:
                    stream.type = "data"
                    stream.path = None
                    stream.data = file.read()
            elif stream.type == "fs":
                stream.data = stream.read()
                stream.type = "data"
            stream.data = image_process(
                stream.data,
                size=(initial_width, initial_height),
                crop=initial_crop,
                quality=quality,
            )
            stream.size = len(stream.data)

        return stream
