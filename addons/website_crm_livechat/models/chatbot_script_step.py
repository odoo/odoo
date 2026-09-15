from odoo import _, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ChatbotScriptStep(models.Model):
    _inherit = "chatbot.script.step"

    def _chatbot_crm_prepare_lead_values(self, discuss_channel, description):
        values = super()._chatbot_crm_prepare_lead_values(discuss_channel, description)
        if discuss_channel.livechat_visitor_id:
            values["name"] = _(
                "%s's New Lead", discuss_channel.livechat_visitor_id.display_name
            )
            values["visitor_ids"] = [(4, discuss_channel.livechat_visitor_id.id)]
            _debug.logic(
                "chatbot_lead_named_after_visitor",
                channel=discuss_channel,
                visitor=discuss_channel.livechat_visitor_id,
            )
        return values
