# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route

from odoo.addons.im_livechat.controllers.chatbot import LivechatChatbotScriptController


class CorsLivechatChatbotScriptController(LivechatChatbotScriptController):
    @route("/chatbot/cors/restart", type="jsonrpc", auth="force_guest", cors="*")
    def cors_chatbot_restart(self, guest_token, channel_id, chatbot_script_id):
        return self.chatbot_restart(channel_id, chatbot_script_id)

    @route("/chatbot/cors/answer/save", type="jsonrpc", auth="force_guest", cors="*")
    def cors_chatbot_save_answer(self, guest_token, channel_id, message_id, selected_answer_id):
        return self.chatbot_save_answer(channel_id, message_id, selected_answer_id)

    @route("/chatbot/cors/step/trigger", type="jsonrpc", auth="force_guest", cors="*")
    def cors_chatbot_trigger_step(
        self,
        guest_token,
        channel_id,
        chatbot_script_id=None,
        data_id=None,
    ):
        return self.chatbot_trigger_step(channel_id, chatbot_script_id, data_id)

    @route("/chatbot/cors/step/validate_contact_info", type="jsonrpc", auth="force_guest", cors="*")
    def cors_chatbot_validate_contact_info(self, guest_token, channel_id):
        return self.chatbot_validate_contact_info(channel_id)
