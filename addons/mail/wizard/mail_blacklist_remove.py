# -*- coding: utf-8 -*-

from odoo import fields, models


class MailBlacklistRemove(models.TransientModel):
    _name = 'mail.blacklist.remove'
    _description = 'Remove email from blacklist wizard'

    email = fields.Char(name="Email", readonly=True, required=True)
    reason = fields.Char(name="Reason")

    def action_unblacklist_apply(self):
        return self.env['mail.blacklist'].action_remove_with_reason(self.email, self.reason)
