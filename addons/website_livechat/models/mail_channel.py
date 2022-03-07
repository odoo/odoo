# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class MailChannel(models.Model):
    _inherit = 'mail.channel'

    livechat_visitor_id = fields.Many2one('website.visitor', string='Visitor')

    def _execute_channel_pin(self, pinned=False):
        """ Override to clean an empty livechat channel.
         This is typically called when the operator send a chat request to a website.visitor
         but don't speak to him and closes the chatter.
         This allows operators to send the visitor a new chat request.
         If active empty livechat channel,
         delete mail_channel as not useful to keep empty chat
         """
        super(MailChannel, self)._execute_channel_pin(pinned)
        if self.livechat_active and not self.message_ids:
            self.unlink()

    def channel_info(self):
        """
        Override to add visitor information on the mail channel infos.
        This will be used to display a banner with visitor informations
        at the top of the livechat channel discussion view in discuss module.
        """
        channel_infos = super().channel_info()
        channel_infos_dict = dict((c['id'], c) for c in channel_infos)
        for channel in self.filtered('livechat_visitor_id'):
            visitor = channel.livechat_visitor_id
            try:
                channel_infos_dict[channel.id]['visitor'] = {
                    'display_name': visitor.display_name,
                    'country_code': visitor.country_id.code.lower() if visitor.country_id else False,
                    'country_id': visitor.country_id.id,
                    'id': visitor.id,
                    'is_connected': visitor.is_connected,
                    'history': self.sudo()._get_visitor_history(visitor),
                    'website_name': visitor.website_id.name,
                    'lang_name': visitor.lang_id.name,
                    'partner_id': visitor.partner_id.id,
                }
            except AccessError:
                pass
        return list(channel_infos_dict.values())

    def _get_visitor_history(self, visitor):
        """
        Prepare history string to render it in the visitor info div on discuss livechat channel view.
        :param visitor: website.visitor of the channel
        :return: arrow separated string containing navigation history information
        """
        recent_history = self.env['website.track'].search([('page_id', '!=', False), ('visitor_id', '=', visitor.id)], limit=3)
        return ' → '.join(visit.page_id.name + ' (' + visit.visit_datetime.strftime('%H:%M') + ')' for visit in reversed(recent_history))

    def _get_visitor_leave_message(self, operator=False, cancel=False):
        name = _('The visitor') if not self.livechat_visitor_id else self.livechat_visitor_id.display_name
        if cancel:
            message = _("""%s has started a conversation with %s. 
                        The chat request has been canceled.""") % (name, operator or _('an operator'))
        else:
            message = _('%s has left the conversation.', name)

        return message

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
