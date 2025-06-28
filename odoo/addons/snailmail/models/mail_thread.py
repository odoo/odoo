# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo import api


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _notify_cancel_snail(self):
        author_id = self.env.user.id
        letters = self.env['snailmail.letter'].search([
            ('state', 'not in', ['sent', 'canceled', 'pending']),
            ('user_id', '=', author_id),
            ('model', '=', self._name)
        ])
        letters.cancel()

    @api.model
    def notify_cancel_by_type(self, notification_type):
        super().notify_cancel_by_type(notification_type)
        if notification_type == 'snail':
            self._notify_cancel_snail()
        return True
