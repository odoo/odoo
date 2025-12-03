# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, http
from odoo.http import request
from odoo.addons.mail.tools.discuss import add_guest_to_context, Store


class LivechatChatbotScriptController(http.Controller):
    @http.route("/chatbot/restart", type="jsonrpc", auth="public")
    @add_guest_to_context
    def chatbot_restart(self, channel_id, chatbot_script_id):
        discuss_channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        chatbot = request.env['chatbot.script'].browse(chatbot_script_id)
        if not discuss_channel or not chatbot.exists():
            return None
        chatbot_language = chatbot._get_chatbot_language()
        message = discuss_channel.with_context(lang=chatbot_language)._chatbot_restart(chatbot)
        store = Store().add(message, "_store_message_fields")
        return {"message_id": message.id, "store_data": store.get_result()}

    @http.route("/chatbot/answer/save", type="jsonrpc", auth="public")
    @add_guest_to_context
    def chatbot_save_answer(self, channel_id, message_id, selected_answer_id):
        discuss_channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        chatbot_message = request.env['chatbot.message'].sudo().search([
            ('mail_message_id', '=', message_id),
            ('discuss_channel_id', '=', discuss_channel.id),
        ], limit=1)
        selected_answer = request.env['chatbot.script.answer'].sudo().browse(selected_answer_id)

        if not discuss_channel or not chatbot_message or not selected_answer.exists():
            return

        if selected_answer in chatbot_message.script_step_id.answer_ids:
            chatbot_message.write({'user_script_answer_id': selected_answer_id})

    @http.route("/chatbot/step/trigger", type="jsonrpc", auth="public")
    @add_guest_to_context
    def chatbot_trigger_step(self, channel_id, chatbot_script_id=None, data_id=None):
        chatbot_language = self.env["chatbot.script"]._get_chatbot_language()
        discuss_channel = request.env["discuss.channel"].with_context(lang=chatbot_language).search([("id", "=", channel_id)])
        if not discuss_channel:
            return None

        next_step = False
        # sudo: chatbot.script.step - visitor can access current step of the script
        if current_step := discuss_channel.sudo().chatbot_current_step_id:
            if (
                current_step.is_forward_operator
                and discuss_channel.livechat_operator_id
                != current_step.chatbot_script_id.operator_partner_id
            ):
                return None
            chatbot = current_step.chatbot_script_id
            domain = [
                ("author_id", "!=", chatbot.operator_partner_id.id),
                ("model", "=", "discuss.channel"),
                ("res_id", "=", channel_id),
            ]
            # sudo: mail.message - accessing last message to process answer is allowed
            user_answer = self.env["mail.message"].sudo().search(domain, order="id desc", limit=1)
            next_step = current_step._process_answer(discuss_channel, user_answer.body)
        elif chatbot_script_id:  # when restarting, we don't have a "current step" -> set "next" as first step of the script
            chatbot = request.env['chatbot.script'].sudo().browse(chatbot_script_id).with_context(lang=chatbot_language)
            if chatbot.exists():
                next_step = chatbot.script_step_ids[:1]
        user, guest = self.env["res.users"]._get_current_persona()
        store = Store(bus_channel=user or guest)
        store.data_id = data_id
        if not next_step:
            # sudo - discuss.channel: marking the channel as closed as part of the chat bot flow
            discuss_channel.sudo().livechat_end_dt = fields.Datetime.now()
            store.resolve_data_request()
            store.bus_send()
            return None
        # sudo: discuss.channel - updating current step on the channel is allowed
        discuss_channel.sudo().chatbot_current_step_id = next_step.id
        posted_message = next_step._process_step(discuss_channel)
        store.add(posted_message, "_store_message_fields")
        store.add(next_step, "_store_script_step_fields")
        chatbot_next_step = {"scriptStep": next_step.id, "message": posted_message.id}
        store.resolve_data_request(lambda res: res.attr("chatbot_step", chatbot_next_step))
        store.add_model_values(
            "ChatbotStep",
            {
                **chatbot_next_step,
                "id": (next_step.id, posted_message.id),
                "isLast": next_step._is_last_step(discuss_channel),
                "operatorFound": next_step.is_forward_operator
                and discuss_channel.livechat_operator_id != chatbot.operator_partner_id,
            },
        )

        store.add_model_values(
            "Chatbot",
            lambda res: (
                res.attr("currentStep", chatbot_next_step),
                res.attr("id", (chatbot.id, discuss_channel.id)),
                res.attr("script", chatbot.id),
                res.one("thread", [], as_thread=True, value=discuss_channel),
                res.attr("steps", [("ADD", [chatbot_next_step])]),
            ),
        )
        store.bus_send()

    @http.route("/chatbot/step/validate_email", type="jsonrpc", auth="public")
    @add_guest_to_context
    def chatbot_validate_email(self, channel_id):
        discuss_channel = (
            request.env["discuss.channel"]
            .search([("id", "=", channel_id)])
            .with_context(lang=self.env["chatbot.script"]._get_chatbot_language())
        )
        if not discuss_channel or not discuss_channel.chatbot_current_step_id:
            return None

        # sudo: chatbot.script - visitor can access chatbot script of their channel
        chatbot = discuss_channel.sudo().chatbot_current_step_id.chatbot_script_id
        domain = [
            ("author_id", "!=", chatbot.operator_partner_id.id),
            ("model", "=", "discuss.channel"),
            ("res_id", "=", channel_id),
        ]
        # sudo: mail.message - accessing last message to validate email is allowed
        last_user_message = self.env["mail.message"].sudo().search(domain, order="id desc", limit=1)
        result = {}
        if last_user_message:
            result = chatbot._validate_email(last_user_message.body, discuss_channel)
            if posted_message := result.pop("posted_message"):
                store = Store().add(
                    discuss_channel,
                    lambda res: res.many(
                        "messages",
                        "_store_message_fields",
                        mode="ADD",
                        value=posted_message,
                    ),
                )
                result["data"] = store.get_result()
        return result
