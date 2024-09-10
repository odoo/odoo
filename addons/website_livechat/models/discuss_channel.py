# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.mail.tools.discuss import Store
from odoo.exceptions import AccessError


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    livechat_visitor_id = fields.Many2one('website.visitor', string='Visitor', index='btree_not_null')

    def channel_pin(self, pinned=False):
        """ Override to clean an empty livechat channel.
         This is typically called when the operator send a chat request to a website.visitor
         but don't speak to them and closes the chatter.
         This allows operators to send the visitor a new chat request.
         If active empty livechat channel,
         delete discuss_channel as not useful to keep empty chat
         """
        super().channel_pin(pinned=pinned)
        if self.livechat_active and not self.message_ids:
            self.sudo().unlink()

    def _to_store(self, store: Store):
        """
        Override to add visitor information on the mail channel infos.
        This will be used to display a banner with visitor informations
        at the top of the livechat channel discussion view in discuss module.
        """
        super()._to_store(store)
        for channel in self.filtered('livechat_visitor_id'):
            channel_info = {
                "requested_by_operator": channel.create_uid in channel.livechat_operator_id.user_ids
            }
            visitor = channel.livechat_visitor_id
            try:
                country_id = visitor.partner_id.country_id or visitor.country_id
                channel_info['visitor'] = {
                    'name': visitor.partner_id.name or visitor.partner_id.display_name or visitor.display_name or _("Visitor #%(id)d.", id=visitor.id),
                    'country': {'id': country_id.id, 'code': country_id.code.lower()} if country_id else False,
                    'id': visitor.id,
                    'is_connected': visitor.is_connected,
                    'history': self.sudo()._get_visitor_history(visitor),
                    'website_name': visitor.website_id.name,
                    'lang_name': visitor.lang_id.name,
                    'partner_id': visitor.partner_id.id,
                    'type': "visitor",
                }
            except AccessError:
                pass
            store.add(channel, channel_info)

    def _get_visitor_history(self, visitor):
        """
        Prepare history string to render it in the visitor info div on discuss livechat channel view.
        :param visitor: website.visitor of the channel
        :return: arrow separated string containing navigation history information
        """
        recent_history = self.env['website.track'].search([('page_id', '!=', False), ('visitor_id', '=', visitor.id)], limit=3)
        return ' → '.join(visit.page_id.name + ' (' + visit.visit_datetime.strftime('%H:%M') + ')' for visit in reversed(recent_history))

    def _get_visitor_leave_message(self, operator=False, cancel=False):
        if not cancel:
            if self.livechat_visitor_id.id:
                return _("Visitor #%(id)d left the conversation.", id=self.livechat_visitor_id.id)
            return _("Visitor left the conversation.")
        return _(
            "%(visitor)s started a conversation with %(operator)s.\nThe chat request has been cancelled",
            visitor=self.livechat_visitor_id.display_name or _("The visitor"),
            operator=operator or _("an operator"),
        )

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        """Override to mark the visitor as still connected.
        If the message sent is not from the operator (so if it's the visitor or
        odoobot sending closing chat notification, the visitor last action date is updated."""
        message = super().message_post(**kwargs)
        message_author_id = message.author_id
        visitor = self.livechat_visitor_id
        if len(self) == 1 and visitor and message_author_id != self.livechat_operator_id:
            # sudo: website.visitor: updating data of a specific visitor
            visitor.sudo()._update_visitor_last_visit()
        return message
