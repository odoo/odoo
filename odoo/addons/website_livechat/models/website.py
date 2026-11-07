# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, Command
from odoo.addons.http_routing.models.ir_http import url_for
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class Website(models.Model):

    _inherit = "website"

    channel_id = fields.Many2one('im_livechat.channel', string='Website Live Chat Channel')

    @add_guest_to_context
    def _get_livechat_channel_info(self):
        """ Get the livechat info dict (button text, channel name, ...) for the livechat channel of
            the current website.
        """
        self.ensure_one()
        if self.channel_id:
            livechat_info = self.channel_id.sudo().get_livechat_info()
            if livechat_info['available']:
                livechat_request_session = self._get_livechat_request_session()
                if livechat_request_session:
                    livechat_info['options']['chat_request_session'] = livechat_request_session
            return livechat_info
        return {}

    def _get_livechat_request_session(self):
        """
        Check if there is an opened chat request for the website livechat channel and the current visitor (from request).
        If so, prepare the livechat session information that will be stored in visitor's cookies
        and used by livechat widget to directly open this session instead of allowing the visitor to
        initiate a new livechat session.
        :param {int} channel_id: channel
        :return: {dict} livechat request session information
        """
        visitor = self.env['website.visitor']._get_visitor_from_request()
        if visitor:
            # get active chat_request linked to visitor
            chat_request_channel = self.env['discuss.channel'].sudo().search([
                ('livechat_visitor_id', '=', visitor.id),
                ('livechat_channel_id', '=', self.channel_id.id),
                ('livechat_active', '=', True),
                ('has_message', '=', True)
            ], order='create_date desc', limit=1)
            if chat_request_channel:
                if not visitor.partner_id:
                    current_guest = self.env['mail.guest']._get_guest_from_context()
                    channel_guest_member = chat_request_channel.channel_member_ids.filtered(lambda m: m.guest_id)
                    if current_guest and current_guest != channel_guest_member.guest_id:
                        # Channel was created with a guest but the visitor was
                        # linked to another guest in the meantime. We need to
                        # update the channel to link it to the current guest.
                        chat_request_channel.write({'channel_member_ids': [Command.unlink(channel_guest_member.id), Command.create({'guest_id': current_guest.id})]})
                    if not current_guest and not channel_guest_member:
                        return {}
                    if not current_guest:
                        channel_guest_member.guest_id._set_auth_cookie()
                        chat_request_channel = chat_request_channel.with_context(guest=channel_guest_member.guest_id.sudo(False))
                return {
                    "folded": False,
                    "id": chat_request_channel.id,
                    "requested_by_operator": chat_request_channel.create_uid in chat_request_channel.livechat_operator_id.user_ids,
                    "operator_pid": [
                        chat_request_channel.livechat_operator_id.id,
                        chat_request_channel.livechat_operator_id.user_livechat_username or chat_request_channel.livechat_operator_id.display_name,
                        chat_request_channel.livechat_operator_id.user_livechat_username,
                    ],
                    "name": chat_request_channel.name,
                    "uuid": chat_request_channel.uuid,
                    "type": "chat_request"
                }
        return {}

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('Live Support'), url_for('/livechat'), 'website_livechat'))
        return suggested_controllers
