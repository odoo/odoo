import typing
from typing import Literal

from odoo import _, fields, models
from odoo.libs.debug_log import DebugLog

if typing.TYPE_CHECKING:
    from ..models.mail_template import MailTemplate

_debug = DebugLog(__name__)


class MailTemplateReset(models.TransientModel):
    _name = "mail.template.reset"
    _description = "Mail Template Reset"

    template_ids: MailTemplate = fields.Many2many(comodel_name="mail.template")

    def reset_template(self) -> dict | Literal[False]:
        if not self.template_ids:
            return False
        _debug.lifecycle(
            "templates_reset", wizard=self.id, templates=self.template_ids.ids
        )
        self.template_ids.reset_template()
        if self.env.context.get("params", {}).get("view_type") == "list":
            next_action = {"type": "ir.actions.client", "tag": "reload"}
        else:
            next_action = {"type": "ir.actions.act_window_close"}
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": _(
                    "The email template(s) have been restored to their original settings."
                ),
                "next": next_action,
            },
        }
