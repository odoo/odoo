# -*- coding: utf-8 -*-

from odoo import fields, models


class PhoneBlacklistRemove(models.TransientModel):
    _name = 'phone.blacklist.remove'
    _description = 'Remove phone from blacklist'

    phone = fields.Char(string="Phone Number", readonly=True, required=True)
    reason = fields.Char(name="Reason")

    def action_unblacklist_apply(self):
        return self.env['phone.blacklist'].action_remove_with_reason(self.phone, self.reason)
