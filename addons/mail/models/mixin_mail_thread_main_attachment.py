import typing

from odoo import fields, models
from odoo.libs.debug_log import DebugLog

from odoo.addons.mail.tools.discuss import Store, StoreFieldsInput

if typing.TYPE_CHECKING:
    from .mail_message import MailMessage
    from odoo.addons.bus.models.ir_attachment import IrAttachment

_debug = DebugLog(__name__)


class MixinMailThreadMainAttachment(models.AbstractModel):
    _name = "mixin.mail.thread.main.attachment"
    _inherit = ["mixin.mail.thread"]
    _description = "Mail Main Attachment management"

    message_main_attachment_id: IrAttachment = fields.Many2one(
        comodel_name="ir.attachment",
        string="Main Attachment",
        index="btree_not_null",
        copy=False,
    )

    def _message_post_after_hook(self, message: MailMessage, msg_values: dict) -> None:
        super()._message_post_after_hook(message, msg_values)
        self.sudo()._message_set_main_attachment_id(
            self.env["ir.attachment"].browse(
                [
                    attachment_command[1]
                    for attachment_command in (msg_values.get("attachment_ids") or [])
                ]
            )
        )

    def _message_set_main_attachment_id(
        self, attachments: IrAttachment, force: bool = False, filter_xml: bool = True
    ) -> None:
        if attachments and (force or not self.message_main_attachment_id):
            if filter_xml:
                attachments = attachments.filtered(
                    lambda r: (
                        not r.mimetype.endswith("xml")
                        and not r.mimetype.endswith("application/octet-stream")
                    )
                )

            if attachments:
                chosen = max(
                    attachments,
                    key=lambda r: (
                        r.mimetype.endswith("pdf"),
                        r.mimetype.startswith("image"),
                    ),
                )
                _debug.lifecycle(
                    "main_attachment_set",
                    model=self._name,
                    record=self.id,
                    attachment=chosen.id,
                    mimetype=chosen.mimetype,
                    candidates=len(attachments),
                    force=force,
                )
                self.with_context(
                    tracking_disable=True
                ).message_main_attachment_id = chosen.id

    def _thread_to_store(
        self,
        store: Store,
        fields: StoreFieldsInput,
        *,
        request_list: list[str] | None = None,
    ) -> None:
        super()._thread_to_store(store, fields, request_list=request_list)
        if request_list and "attachments" in request_list:
            store.add(
                self,
                Store.One("message_main_attachment_id", []),
                as_thread=True,
            )
