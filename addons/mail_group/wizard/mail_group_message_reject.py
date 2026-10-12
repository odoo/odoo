# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _


class MailGroupMessageReject(models.TransientModel):
    _name = 'mail.group.message.reject'
    _description = 'Reject Group Message'

    subject = fields.Char('Subject', store=True, readonly=False, compute='_compute_subject')
    body = fields.Html('Contents', default='', sanitize_style=True)
    email_from_normalized = fields.Char('Email From', related='mail_group_message_id.email_from_normalized')
    mail_group_message_id = fields.Many2one('mail.group.message', string="Message", required=True, readonly=True)
    action = fields.Selection([('reject', 'Reject'), ('ban', 'Ban')], string='Action', required=True)

    send_email = fields.Boolean('Send Email', help='Send an email to the author of the message', compute='_compute_send_email')

    @api.depends('mail_group_message_id')
    def _compute_subject(self):
        for wizard in self:
            wizard.subject = _('Re: %s', wizard.mail_group_message_id.subject or '')

    @api.depends('body')
    def _compute_send_email(self):
        for wizard in self:
            wizard.send_email = not tools.is_html_empty(wizard.body)

    def action_send_mail(self):
        self.ensure_one()

        # Reject
        if self.action == 'reject' and self.send_email:
            self.mail_group_message_id.action_moderate_reject_with_comment(self.subject, self.body)
        elif self.action == 'reject' and not self.send_email:
            self.mail_group_message_id.action_moderate_reject()

        # Ban
        elif self.action == 'ban' and self.send_email:
            self.mail_group_message_id.action_moderate_ban_with_comment(self.subject, self.body)
        elif self.action == 'ban' and not self.send_email:
            self.mail_group_message_id.action_moderate_ban()
