# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ChatbotScriptStep(models.Model):
    _inherit = 'chatbot.script.step'

    def _chatbot_prepare_customer_values(self, mail_channel, create_partner=True, update_partner=True):
        values = super()._chatbot_prepare_customer_values(mail_channel, create_partner, update_partner)
        visitor_id = mail_channel.livechat_visitor_id
        if visitor_id:
            if not values.get('email') and visitor_id.email:
                values['email'] = visitor_id.email
            if not values.get('phone') and visitor_id.mobile:
                values['phone'] = visitor_id.mobile
            values['country_id'] = visitor_id.country_id

        return values
