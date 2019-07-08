# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailChannel(models.Model):
    _inherit = 'mail.channel'

    livechat_request_ids = fields.One2many('im_livechat.request', 'mail_channel_id', string='Chat Request')
    livechat_visitor_id = fields.Many2one('website.visitor', string='Visitor')
    livechat_active = fields.Boolean('Is livechat ongoing?', help='Livechat session is not considered as active if the visitor left the conversation.')

    def _execute_channel_pin(self, pinned=False):
        """ Override to clean an empty livechat channel.
         This is typically called when the operator send a chat request to a website.visitor
         but don't speak to him and closes the chatter.
         This allows operators to send the visitor a new chat request."""
        super(MailChannel, self)._execute_channel_pin(pinned)
        # If active empty livechat channel
        if self.livechat_active and not self.channel_message_ids:
            # delete the chat request if any
            if self.livechat_request_ids:
                for chat_request in self.livechat_request_ids:
                    chat_request.unlink()
            # delete the mail channel as not useful to keep empty chat
            self.unlink()
