from __future__ import annotations

import typing

from odoo import models

from odoo.addons.mail.tools.discuss import Store

if typing.TYPE_CHECKING:
    from odoo.addons.mail.tools.discuss import StoreFieldsInput


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _to_store_defaults(self, target: Store.Target) -> StoreFieldsInput:
        return super()._to_store_defaults(target) + [
            "can_transcribe",
            "transcript_state",
            "transcript_text",
        ]

    def _notify_transcript_owner(self, transcribed: bool) -> None:
        super()._notify_transcript_owner(transcribed)
        for attachment in self:
            for message in attachment._speech_messages():
                Store(bus_channel=message._bus_channel()).add(
                    attachment,
                    ["transcript_state", "transcript_text"],
                ).bus_send()

    def _speech_messages(self) -> models.Model:
        self.check_singleton()
        return (
            self.env["mail.message"].sudo().search([("attachment_ids", "in", self.ids)])
        )
