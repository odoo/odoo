# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class ImLivechatChannel(models.Model):
    _inherit = 'im_livechat.channel'

    def _get_livechat_mail_channel_vals(self, anonymous_name, operator, user_id=None, country_id=None):
        mail_channel_vals = super(ImLivechatChannel, self)._get_livechat_mail_channel_vals(anonymous_name, operator, user_id=user_id, country_id=country_id)
        visitor_sudo = self.env['website.visitor']._get_visitor_from_request()
        if visitor_sudo:
            mail_channel_vals.update({
                'livechat_visitor_id': visitor_sudo.id,
                'livechat_active': True
            })
            if not user_id:
                mail_channel_vals['anonymous_name'] = visitor_sudo.display_name + (' (%s)' % visitor_sudo.country_id.name if visitor_sudo.country_id else '')
            # As chat requested by the visitor, delete the chat requested by an operator if any to avoid conflicts between two flows
            chat_request_channel = self.env['mail.channel'].sudo().search([('livechat_visitor_id', '=', visitor_sudo.id), ('livechat_active', '=', True)])
            for mail_channel in chat_request_channel:
                mail_channel.close_livechat_request_session(type='cancel', speaking_with=operator.name)

        return mail_channel_vals
