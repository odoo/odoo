import typing
from typing import Literal, Self

from odoo import api, fields, models, tools
from odoo.api import ValuesType
from odoo.libs.debug_log import DebugLog

if typing.TYPE_CHECKING:
    from odoo.addons.mail.models.base import SuggestionSources

_debug = DebugLog(__name__)


class MixinMailThreadCc(models.AbstractModel):
    _name = "mixin.mail.thread.cc"
    _inherit = ["mixin.mail.thread"]
    _description = "Email CC management"

    email_cc = fields.Char(string="Email cc")

    def _mail_cc_sanitized_raw_dict(self, cc_string: str | Literal[False]) -> dict:
        if not cc_string:
            return {}
        sanitized = {}
        for name, email in tools.mail.email_split_tuples(cc_string):
            normalized = tools.email_normalize(email)
            if not normalized:
                continue
            sanitized[normalized] = tools.formataddr((name, normalized))
        return sanitized

    @api.model
    def message_new(self, msg_dict: dict, custom_values: dict | None = None) -> Self:
        if custom_values is None:
            custom_values = {}
        cc_values = {
            "email_cc": ", ".join(
                self._mail_cc_sanitized_raw_dict(msg_dict.get("cc")).values()
            ),
        }
        cc_values.update(custom_values)
        return super().message_new(msg_dict, cc_values)

    def message_update(
        self, msg_dict: dict, update_vals: ValuesType | None = None
    ) -> bool:
        if update_vals is None:
            update_vals = {}
        cc_values = {}
        new_cc = self._mail_cc_sanitized_raw_dict(msg_dict.get("cc"))
        if new_cc:
            old_cc = self._mail_cc_sanitized_raw_dict(self.email_cc)
            _debug.logic(
                "cc_merged",
                model=self._name,
                records=self.ids,
                new=len(new_cc),
                old=len(old_cc),
            )
            new_cc.update(old_cc)
            cc_values["email_cc"] = ", ".join(new_cc.values())
        cc_values.update(update_vals)
        return super().message_update(msg_dict, cc_values)

    def _message_get_suggested_recipients_sources(
        self, force_primary_email: str | Literal[False] = False
    ) -> dict[int, SuggestionSources]:
        suggested = super()._message_get_suggested_recipients_sources(
            force_primary_email=force_primary_email
        )
        for record in self.filtered("email_cc"):
            suggested[record.id]["email_to_lst"] += (
                tools.mail.email_split_and_format_normalize(record.email_cc)
            )
        return suggested
