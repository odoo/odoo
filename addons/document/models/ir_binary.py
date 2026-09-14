from os.path import splitext
from typing import Any

from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class IrBinary(models.AbstractModel):
    _inherit = "ir.binary"

    def _record_to_stream(self, record: models.Model, field_name: str) -> Any:
        if record._name == "document.document" and field_name in ("raw", "datas"):
            _debug.logic("stream_from_attachment", document=record, field=field_name)
            return super()._record_to_stream(record.attachment_id.sudo(), field_name)

        return super()._record_to_stream(record, field_name)

    def _get_stream_from_record(
        self,
        record: models.Model,
        field_name: str = "raw",
        filename: str | None = None,
        filename_field: str = "name",
        mimetype: str | None = None,
        default_mimetype: str = "application/octet-stream",
    ) -> Any:
        if (
            record._name == "document.document"
            and filename is None
            and record.file_extension
        ):
            name, extension = splitext(record.name)  # noqa: PTH122  a display name, not a path
            if extension == f".{record.file_extension}":
                filename = record.name
            else:
                filename = f"{name}.{record.file_extension}"
        if (
            record._name in ("document.document", "ir.attachment")
            and record.mimetype == "application/documents-email"
        ):
            _debug.logic("stream_mimetype_rewritten", record=record, to="text/plain")
            mimetype = "text/plain"
        return super()._get_stream_from_record(
            record, field_name, filename, filename_field, mimetype, default_mimetype
        )
