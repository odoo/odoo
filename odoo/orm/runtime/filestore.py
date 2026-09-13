from __future__ import annotations

import typing

from odoo.libs.debug_log import DebugLog
from odoo.tools import human_size

if typing.TYPE_CHECKING:
    from odoo.tools import Query

    from .._protocols import IrAttachmentProtocol
    from .._typing import BaseModel
    from .environment import Environment

_debug = DebugLog(__name__)


def _field_domain(model_name: str, field_name: str, res_ids: list[int]) -> list:
    return [
        ("res_model", "=", model_name),
        ("res_field", "=", field_name),
        ("res_id", "in", res_ids),
    ]


class FileStore:
    __slots__ = ()

    def _attachments(self, env: Environment) -> IrAttachmentProtocol:
        return env["ir.attachment"].sudo()

    def read_field(
        self, records: BaseModel, field_name: str, *, bin_size: bool
    ) -> dict[int, typing.Any]:
        attachments = self._attachments(records.env)._with_bin_size_disabled()
        return {
            att.res_id: (human_size(att.file_size) if bin_size else att.datas)
            for att in attachments.search_fetch(
                _field_domain(records._name, field_name, records.ids)
            )
        }

    def of_field(self, records: BaseModel, field_name: str) -> BaseModel:
        return self._attachments(records.env).search(
            _field_domain(records._name, field_name, records.ids)
        )

    def of_records(self, records: BaseModel) -> BaseModel:
        # every file behind the records, the field-owned ones included, which the
        # attachment model's search hides unless told otherwise
        return (
            self._attachments(records.env)
            .with_context(skip_res_field_check=True)
            .search([("res_model", "=", records._name), ("res_id", "in", records.ids)])
        )

    def create_field(
        self,
        env: Environment,
        model_name: str,
        field_name: str,
        values: typing.Iterable[tuple[int, typing.Any]],
    ) -> BaseModel:
        return self._attachments(env).create(
            [
                {
                    "name": field_name,
                    "res_model": model_name,
                    "res_field": field_name,
                    "res_id": res_id,
                    "type": "binary",
                    "datas": value,
                }
                for res_id, value in values
            ]
        )

    def field_set_query(self, model: BaseModel, field_name: str) -> Query:
        attachments = typing.cast("BaseModel", self._attachments(model.env))
        return attachments._search(
            [
                ("res_model", "=", model._name),
                ("res_field", "=", field_name),
                ("res_id", ">", 0),
            ]
        )

    def resized_webp(self, env: Environment, image: bytes, size: int) -> typing.Any:
        Attachment = env["ir.attachment"]
        checksum = Attachment._get_content_checksum(image)
        origins = Attachment.search([("id", "!=", False), ("checksum", "=", checksum)])
        if not origins:
            return None
        resized = Attachment.sudo().search(
            [
                ("id", "!=", False),
                ("res_model", "=", "ir.attachment"),
                ("res_id", "in", origins.ids),
                ("description", "=", f"resize: {size}"),
            ],
            limit=1,
        )
        _debug.logic(
            "filestore.webp_resize_lookup",
            origins=len(origins),
            resized=bool(resized),
        )
        return resized.datas if resized else None


FILE_STORE = FileStore()
