# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class MailChannel(models.Model):
    _inherit = 'mail.channel'

    livechat_visitor_id = fields.Many2one('website.visitor', string='Visitor')
    livechat_active = fields.Boolean('Is livechat ongoing?', help='Livechat session is not considered as active if the visitor left the conversation.')

    def _execute_channel_pin(self, pinned=False):
        """ Override to clean an empty livechat channel.
         This is typically called when the operator send a chat request to a website.visitor
         but don't speak to him and closes the chatter.
         This allows operators to send the visitor a new chat request.
         If active empty livechat channel,
         delete mail_channel as not useful to keep empty chat
         """
        super(MailChannel, self)._execute_channel_pin(pinned)
        if self.livechat_active and not self.channel_message_ids:
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
                    'partner_id': visitor.user_partner_id.id,
                }
        return list(channel_infos_dict.values())

    def _get_visitor_history(self, visitor):
        """
        Prepare history string to render it in the visitor info div on discuss livechat channel view.
        :param visitor: website.visitor of the channel
        :return: arrow separated string containing navigation history information
        """
        recent_history = visitor.visitor_page_ids[:3] if len(visitor.visitor_page_ids) >= 3 else visitor.visitor_page_ids
        return ' → '.join(page.page_id.name + ' (' + page.visit_datetime.strftime('%H:%M') + ')' for page in recent_history)

    def close_livechat_request_session(self, message):
        self.ensure_one()
        if self.livechat_active:
            self.livechat_active = False
            # Notify that the visitor has left the conversation
            name = _('The visitor') if not self.livechat_visitor_id else self.livechat_visitor_id.name
            leave_message = '%s %s' % (name, message)
            self.message_post(author_id=self.env.ref('base.user_root').sudo().partner_id.id,
                              body=leave_message, message_type='comment', subtype='mt_comment')

    def message_post(self, **kwargs):
        """Override to mark the visitor as still connected.
        If the message sent is not from the operator (so if it's the visitor or
        odoobot sending closing chat notification, the visitor last action date is updated."""
        message = super(MailChannel, self).message_post(**kwargs)
        message_author_id = message.author_id
        visitor = self.livechat_visitor_id
        if len(self) == 1 and visitor and message_author_id != self.livechat_operator_id:
            visitor.sudo().write({
                'last_connection_datetime': fields.datetime.now(),
            })
        return message

