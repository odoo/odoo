# -*- coding: utf-8 -*-

from markupsafe import Markup
from odoo import fields, models, _


class MailBlacklistRemove(models.TransientModel):
    _name = 'mail.blacklist.remove'
    _description = 'Remove email from blacklist wizard'

    email = fields.Char(name="Email", readonly=True, required=True)
    reason = fields.Char(name="Reason")

    def action_unblacklist_apply(self):
        if self.reason:
            message = Markup('<p>%s</p>') % _("Unblock Reason: %(reason)s", reason=self.reason)
        else:
            message = None
        return self.env['mail.blacklist']._remove(
            self.email,
            message=message,
        )
