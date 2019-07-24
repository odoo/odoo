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

    def channel_info(self, extra_info=False):
        """
        Override to add visitor information on the mail channel infos.
        This will be used to display a banner with visitor informations
        at the top of the livechat channel discussion view in discuss module.
        """
        channel_infos = super(MailChannel, self).channel_info(extra_info)
        channel_infos_dict = dict((c['id'], c) for c in channel_infos)
        for channel in self:
            visitor = channel.livechat_visitor_id
            if visitor:
                channel_infos_dict[channel.id]['visitor'] = {
                    'name': visitor.name,
                    'country_code': visitor.country_id.code.lower() if visitor.country_id else False,
                    'is_connected': visitor.is_connected,
                    'history': self._get_visitor_history(visitor),
                    'website': visitor.website_id.name,
                    'lang': visitor.lang_id.name,
                }
        return list(channel_infos_dict.values())

    def _get_visitor_history(self, visitor):
        """
        Prepare history string to render it in the visitor info div on discuss livechat channel view.
        :param visitor: website.visitor of the channel
        :return: arrow separated string containing navigation history information
        """
        history = ""
        recent_history = visitor.page_ids[:3] if len(visitor.page_ids) >= 3 else visitor.page_ids
        inverse_index = len(recent_history) - 1
        while inverse_index > -1:
            page = recent_history[inverse_index]
            history += page.page_id.name + ' (' + page.visit_date.strftime('%H:%M') + ')'
            if inverse_index != 0:
                history += ' → '
            inverse_index -= 1
        return history
