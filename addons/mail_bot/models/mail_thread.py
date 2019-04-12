# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _message_post_after_hook(self, message, msg_vals):
        self.env['mail.bot']._apply_logic(self, msg_vals)
        return super(MailThread, self)._message_post_after_hook(message, msg_vals)
