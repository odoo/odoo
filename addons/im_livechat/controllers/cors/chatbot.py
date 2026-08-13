# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route
from odoo.addons.im_livechat.controllers.chatbot import LivechatChatbotScriptController
from odoo.addons.im_livechat.tools.misc import force_guest_env


class CorsLivechatChatbotScriptController(LivechatChatbotScriptController):
    @route("/chatbot/cors/restart", type="json", auth="public", cors="*")
    def cors_chatbot_restart(self, guest_token, channel_id, chatbot_script_id):
        force_guest_env(guest_token)
        return self.chatbot_restart(channel_id, chatbot_script_id)

    @route("/chatbot/cors/answer/save", type="json", auth="public", cors="*")
    def cors_chatbot_save_answer(self, guest_token, channel_id, message_id, selected_answer_id):
        force_guest_env(guest_token)
        return self.chatbot_save_answer(channel_id, message_id, selected_answer_id)

    @route("/chatbot/cors/step/trigger", type="json", auth="public", cors="*")
    def cors_chatbot_trigger_step(self, guest_token, channel_id, chatbot_script_id=None):
        force_guest_env(guest_token)
        return self.chatbot_trigger_step(channel_id, chatbot_script_id)

    @route("/chatbot/cors/step/validate_email", type="json", auth="public", cors="*")
    def cors_chatbot_validate_email(self, guest_token, channel_id):
        force_guest_env(guest_token)
        return self.chatbot_validate_email(channel_id)
