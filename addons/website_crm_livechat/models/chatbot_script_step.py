
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class ChatbotScriptStep(models.Model):
    _inherit = 'chatbot.script.step'

    def _chatbot_crm_prepare_lead_values(self, mail_channel, description):
        values = super()._chatbot_crm_prepare_lead_values(mail_channel, description)
        if mail_channel.livechat_visitor_id:
            values['name'] = _("%s's New Lead", mail_channel.livechat_visitor_id.display_name)
            values['visitor_ids'] = [(4, mail_channel.livechat_visitor_id.id)]
        return values
