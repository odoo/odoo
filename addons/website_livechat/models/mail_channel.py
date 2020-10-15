# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


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
                    'name': visitor.display_name,
                    'country_code': visitor.country_id.code.lower() if visitor.country_id else False,
                    'is_connected': visitor.is_connected,
                    'history': self._get_visitor_history(visitor),
                    'website': visitor.website_id.name,
                    'lang': visitor.lang_id.name,
                    'partner_id': visitor.partner_id.id,
                }
        return list(channel_infos_dict.values())

    def _get_visitor_history(self, visitor):
        """
        Prepare history string to render it in the visitor info div on discuss livechat channel view.
        :param visitor: website.visitor of the channel
        :return: arrow separated string containing navigation history information
        """
        recent_history = self.env['website.track'].search([('page_id', '!=', False), ('visitor_id', '=', visitor.id)], limit=3)
        return ' → '.join(visit.page_id.name + ' (' + visit.visit_datetime.strftime('%H:%M') + ')' for visit in reversed(recent_history))

    def close_livechat_request_session(self, type='leave', **kwargs):
        """ Set deactivate the livechat channel and notify (the operator) the reason of closing the session."""
        self.ensure_one()
        if self.livechat_active:
            self.livechat_active = False
            # avoid useless notification if the channel is empty
            if not self.channel_message_ids:
                return
            # Notify that the visitor has left the conversation
            name = _('The visitor') if not self.livechat_visitor_id else self.livechat_visitor_id.display_name
            if type == 'cancel':
                message = _('has started a conversation with %s. The chat request has been canceled.') % kwargs.get('speaking_with', 'an operator')
            else:
                message = _('has left the conversation.')
            leave_message = '%s %s' % (name, message)
            self.message_post(author_id=self.env.ref('base.user_root').sudo().partner_id.id,
                              body=leave_message, message_type='comment', subtype='mt_comment')

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        """Override to mark the visitor as still connected.
        If the message sent is not from the operator (so if it's the visitor or
        odoobot sending closing chat notification, the visitor last action date is updated."""
        message = super(MailChannel, self).message_post(**kwargs)
        message_author_id = message.author_id
        visitor = self.livechat_visitor_id
        if len(self) == 1 and visitor and message_author_id != self.livechat_operator_id:
            visitor._update_visitor_last_visit()
        return message
