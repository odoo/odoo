import contextlib
import typing

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import (
    is_valid_limited_field_access_token,
    limited_field_access_token,
)

from odoo.addons.mail.tools.discuss import Store, StoreFieldsInput, StoreFieldSpec

if typing.TYPE_CHECKING:
    from .mail_message import MailMessage

_debug = DebugLog(__name__)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    thumbnail = fields.Image()
    has_thumbnail = fields.Boolean(compute="_compute_has_thumbnail")

    @api.depends("thumbnail")
    def _compute_has_thumbnail(self) -> None:
        for attachment in self.with_context(bin_size=True):
            attachment.has_thumbnail = bool(attachment.thumbnail)

    def _has_attachments_ownership(
        self, attachment_tokens: list[str | None] | None
    ) -> bool:
        attachment_tokens = attachment_tokens or ([None] * len(self))
        if len(attachment_tokens) != len(self):
            raise UserError(
                self.env._("An access token must be provided for each attachment.")
            )

        def is_owned(attachment: IrAttachment, token: str) -> bool:
            if not attachment.exists():
                return False
            if attachment.sudo(False).has_access("write"):
                return True
            return token and is_valid_limited_field_access_token(
                attachment, "id", token, scope="attachment_ownership"
            )

        return all(map(is_owned, self, attachment_tokens, strict=True))

    @api.model_create_multi
    def create(self, vals_list):
        attachments = super().create(vals_list)
        attachments._invalidate_thread_attachment_count()
        return attachments

    def write(self, vals):
        invalidate = "res_model" in vals or "res_id" in vals
        if invalidate:
            self._invalidate_thread_attachment_count()
        res = super().write(vals)
        if invalidate:
            self._invalidate_thread_attachment_count()
        return res

    def unlink(self):
        self._invalidate_thread_attachment_count()
        return super().unlink()

    def _invalidate_thread_attachment_count(self) -> None:
        by_model = {}
        for attachment in self:
            if attachment.res_model and attachment.res_id:
                by_model.setdefault(attachment.res_model, set()).add(attachment.res_id)
        if _debug.perf.enabled and by_model:
            _debug.perf.count(
                "attachment_count_invalidated",
                attachments=len(self),
                models=sorted(by_model),
            )
        for model_name, res_ids in by_model.items():
            model = self.env.get(model_name)
            if model is None or "message_attachment_count" not in model._fields:
                continue
            model.browse(res_ids).invalidate_recordset(
                ["message_attachment_count"], flush=False
            )

    def _post_add_create(self, **kwargs) -> None:
        super()._post_add_create(**kwargs)
        self.register_as_main_attachment(force=False)

    def register_as_main_attachment(self, force: bool = True) -> None:
        todo = self.filtered(lambda a: a.res_model and a.res_id)
        if not todo:
            return

        for model, attachments in todo.grouped("res_model").items():
            if model not in self.env:
                continue
            related_records = self.env[model].browse(attachments.mapped("res_id"))
            if not hasattr(related_records, "_message_set_main_attachment_id"):
                continue
            _debug.lifecycle(
                "main_attachment_registered",
                model=model,
                attachments=len(attachments),
                force=force,
            )

            for related_record, attachment in zip(
                related_records, attachments, strict=False
            ):
                with contextlib.suppress(AccessError):
                    related_record._message_set_main_attachment_id(
                        attachment, force=force
                    )

    def _remove_and_notify(self, message: MailMessage | None = None) -> None:
        if message:
            message.sudo().write({})
        _debug.lifecycle(
            "removed_and_notified",
            attachments=self.ids,
            message=message.id if message else None,
        )
        for attachment in self:
            attachment._bus_send(
                "ir.attachment/delete",
                {
                    "id": attachment.id,
                    "message": (
                        {"id": message.id, "write_date": message.write_date}
                        if message
                        else None
                    ),
                },
            )
        self.unlink()

    def _get_fields_store_ownership(self) -> list[StoreFieldSpec]:
        return [Store.Attr("ownership_token", lambda a: a._get_ownership_token())]

    def _to_store_defaults(self, target: Store.Target) -> StoreFieldsInput:
        return [
            "checksum",
            "create_date",
            "file_size",
            "has_thumbnail",
            "mimetype",
            "name",
            Store.Attr("raw_access_token", lambda a: a._get_raw_access_token()),
            "res_name",
            "res_model",
            Store.One("thread", [], as_thread=True),
            Store.Attr("thumbnail_access_token", lambda a: a._get_thumbnail_token()),
            "type",
            "url",
        ]

    def _get_ownership_token(self) -> str:
        self.check_singleton()
        return limited_field_access_token(
            self, field_name="id", scope="attachment_ownership"
        )

    def _get_thumbnail_token(self) -> str:
        self.check_singleton()
        return limited_field_access_token(self, "thumbnail", scope="binary")
