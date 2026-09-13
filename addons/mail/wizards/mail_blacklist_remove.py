import typing

from markupsafe import Markup

from odoo import _, fields, models
from odoo.libs.debug_log import DebugLog

if typing.TYPE_CHECKING:
    from ..models.mail_blacklist import MailBlacklist

_debug = DebugLog(__name__)


class MailBlacklistRemove(models.TransientModel):
    _name = "mail.blacklist.remove"
    _description = "Remove email from blacklist wizard"

    email = fields.Char(
        readonly=True,
        required=True,
        name="Email",
    )
    reason = fields.Char(name="Reason")

    def action_unblacklist_apply(self) -> MailBlacklist:
        if self.reason:
            message = Markup("<p>%s</p>") % _(
                "Unblock Reason: %(reason)s", reason=self.reason
            )
        else:
            message = None
        _debug.lifecycle("unblacklist", wizard=self.id, with_reason=bool(self.reason))
        return self.env["mail.blacklist"]._remove(
            self.email,
            message=message,
        )
