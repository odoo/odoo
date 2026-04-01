# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ChatbotScriptStep(models.Model):
    _inherit = 'chatbot.script.step'

    def _chatbot_prepare_customer_values(self, discuss_channel, create_partner=True, update_partner=True):
        values = super()._chatbot_prepare_customer_values(discuss_channel, create_partner, update_partner)
        # sudo - website.visitor: chat bot can access visitor information
        if visitor_sudo := discuss_channel.livechat_visitor_id.sudo():
            if not values.get('email') and visitor_sudo.email:
                values['email'] = visitor_sudo.email
            if not values.get('phone') and visitor_sudo.mobile:
                values['phone'] = visitor_sudo.mobile
            values['country'] = {'id': visitor_sudo.country_id} if visitor_sudo.country_id else False

        return values
