# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailGroupMessageReject(models.TransientModel):
    _name = 'mail.group.message.reject'
    _description = 'Reject Group Message'

    subject = fields.Char('Subject')
    body = fields.Html('Contents', default='', sanitize_style=True)

    mail_group_message_id = fields.Many2one('mail.group.message', string="Message", required=True, readonly=True)

    def action_send_mail(self):
        self.ensure_one()
        self.mail_group_message_id.action_moderate_reject_with_comment(self.subject, self.body)
