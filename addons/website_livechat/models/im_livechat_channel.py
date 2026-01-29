# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class ImLivechatChannel(models.Model):
    _inherit = 'im_livechat.channel'

    def _get_livechat_discuss_channel_vals(self, anonymous_name, previous_operator_id=None, chatbot_script=None, user_id=None, country_id=None, lang=None):
        discuss_channel_vals = super(ImLivechatChannel, self)._get_livechat_discuss_channel_vals(
            anonymous_name, previous_operator_id, chatbot_script, user_id=user_id, country_id=country_id, lang=lang
        )
        if not discuss_channel_vals:
            return False
        visitor_sudo = self.env['website.visitor']._get_visitor_from_request()
        if visitor_sudo:
            discuss_channel_vals['livechat_visitor_id'] = visitor_sudo.id
            # As chat requested by the visitor, delete the chat requested by an operator if any to avoid conflicts between two flows
            # TODO DBE : Move this into the proper method (open or init mail channel)
            chat_request_channel = self.env['discuss.channel'].sudo().search([('livechat_visitor_id', '=', visitor_sudo.id), ('livechat_active', '=', True)])
            for discuss_channel in chat_request_channel:
                operator = discuss_channel.livechat_operator_id
                operator_name = operator.user_livechat_username or operator.name
                discuss_channel._close_livechat_session(cancel=True, operator=operator_name)

        return discuss_channel_vals
