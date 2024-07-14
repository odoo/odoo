# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class SocialMediaPushNotifications(models.Model):
    _inherit = 'social.media'

    media_type = fields.Selection(selection_add=[('push_notifications', 'Push Notifications')])

    def _action_add_account(self):
        self.ensure_one()

        if self.media_type != 'push_notifications':
            return super(SocialMediaPushNotifications, self)._action_add_account()

        return None
