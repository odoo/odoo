from __future__ import annotations

import typing

from markupsafe import Markup

from odoo import Command, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

from ..tools.speech import READ_ALOUD_MAX_CHARS

if typing.TYPE_CHECKING:
    from odoo.addons.base.models.ir_attachment import IrAttachment


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _speech_text(self) -> str:
        self.check_singleton()
        body = self.body or Markup("")
        return html2plaintext(body).strip()

    def action_read_aloud(self, voice: str | None = None) -> IrAttachment:
        self.check_singleton()
        self.check_access("read")
        text = self._speech_text()
        if not text:
            raise UserError(self.env._("There is nothing in this message to read."))
        if len(text) > READ_ALOUD_MAX_CHARS:
            raise UserError(
                self.env._(
                    "This message is too long to read aloud: %(count)s characters "
                    "against a limit of %(limit)s.",
                    count=len(text),
                    limit=READ_ALOUD_MAX_CHARS,
                )
            )
        attachment = self.env["ir.attachment"]._speech_synthesize(
            text,
            voice=voice,
            language=self.env.user.lang,
            name=self.env._("Read aloud.mp3"),
            res_model=self._name,
            res_id=self.id,
        )
        self.sudo().attachment_ids = [Command.link(attachment.id)]
        return attachment
