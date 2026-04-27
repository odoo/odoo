# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

SIGN_USER_FIELDS = ['sign_signature', 'sign_initials']

class ResUsers(models.Model):
    _inherit = 'res.users'

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + SIGN_USER_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + SIGN_USER_FIELDS

    sign_signature = fields.Binary(string="Digital Signature", copy=False, groups="base.group_system")
    sign_initials = fields.Binary(string="Digital Initials", copy=False, groups="base.group_system")
    sign_signature_frame = fields.Binary(string="Digital Signature Frame", copy=False, groups="base.group_system")
    sign_initials_frame = fields.Binary(string="Digital Initials Frame", copy=False, groups="base.group_system")
