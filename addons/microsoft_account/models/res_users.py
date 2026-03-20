# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta


from odoo import api, fields, models, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    microsoft_calendar_rtoken = fields.Char('Microsoft Refresh Token', copy=False, groups="base.group_system")
    microsoft_calendar_token = fields.Char('Microsoft User token', copy=False, groups="base.group_system")
    microsoft_calendar_token_validity = fields.Datetime('Microsoft Token Validity', copy=False)

    def _set_microsoft_auth_tokens(self, access_token, refresh_token, ttl):
        self.write({
            'microsoft_calendar_rtoken': refresh_token,
            'microsoft_calendar_token': access_token,
            'microsoft_calendar_token_validity': fields.Datetime.now() + timedelta(seconds=ttl) if ttl else False,
        })
