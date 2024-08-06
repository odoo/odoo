# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.addons.http_routing.models.ir_http import url_for


class Website(models.Model):

    _inherit = "website"

    channel_id = fields.Many2one('im_livechat.channel', string='Website Live Chat Channel')

    def get_livechat_channel_info(self):
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
            chat_request_channel = self.env['mail.channel'].sudo().search([
                ('livechat_visitor_id', '=', visitor.id),
                ('livechat_channel_id', '=', self.channel_id.id),
                ('livechat_active', '=', True),
                ('channel_message_ids', '!=', False)
            ], order='create_date desc', limit=1)
            if chat_request_channel:
                return {
                    "folded": False,
                    "id": chat_request_channel.id,
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
