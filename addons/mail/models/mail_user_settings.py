# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailUserSettings(models.Model):
    _name = 'mail.user.settings'
    _description = 'Mail User Settings'

    is_discuss_sidebar_category_channel_open = fields.Boolean(string="Is discuss sidebar category channel open?", default=True)
    is_discuss_sidebar_category_chat_open = fields.Boolean(string="Is discuss sidebar category chat open?", default=True)
    user_id = fields.Many2one('res.users', string="User", required=True, index=True)

    _sql_constraints = [
        ('unique_user_id', 'UNIQUE(user_id)', 'One user should only have one mail user settings.')
    ]

    @api.model
    def find_or_create_for_user(self, user):
        settings = user.mail_user_settings
        if not settings:
            settings = self.create({'user_id': user.id})
        return settings

    def mail_user_settings_format(self):
        self.ensure_one
        return self.read()[0]

    def set_mail_user_settings(self, new_settings):
        self.ensure_one()
        self.write(new_settings)
        notification = {
            'type': 'mail_user_settings',
            'payload': self.mail_user_settings_format()
        }
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.user_id.partner_id.id), notification)
