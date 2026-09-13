from odoo import models

from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _to_store_defaults(self, target):
        return super()._to_store_defaults(target) + ["chatbot_current_step"]

    def _to_store(self, store: Store, fields, **kwargs):
        super()._to_store(
            store, [f for f in fields if f != "chatbot_current_step"], **kwargs
        )
        if "chatbot_current_step" not in fields:
            return
        channel_messages = self.filtered(lambda message: message.channel_id)
        channel_by_message = channel_messages._record_by_message()
        for message in channel_messages.filtered(
            lambda message: channel_by_message[message].channel_type == "livechat"
        ):
            channel = channel_by_message[message]
            chatbot = channel.chatbot_current_step_id.sudo().chatbot_script_id.operator_partner_id
            if channel.chatbot_current_step_id and message.author_id == chatbot:
                chatbot_message = (
                    self.env["chatbot.message"]  # noqa: E8507 - one lookup per chatbot message, on its own step
                    .sudo()
                    .search([("mail_message_id", "=", message.id)], limit=1)
                )
                if step := chatbot_message.script_step_id:
                    step_data = {
                        "id": (step.id, message.id),
                        "message": message.id,
                        "scriptStep": Store.One(step, ["id", "message", "step_type"]),
                        "operatorFound": step.is_forward_operator
                        and channel.livechat_operator_id != chatbot,
                    }
                    if answer := chatbot_message.user_script_answer_id:
                        step_data["selectedAnswer"] = {
                            "id": answer.id,
                            "label": answer.name,
                        }
                    if step.step_type in [
                        "free_input_multi",
                        "free_input_single",
                        "question_email",
                        "question_phone",
                    ]:
                        user_answer_message = (
                            self.env["chatbot.message"]  # noqa: E8507 - one lookup per chatbot message, on its own step
                            .sudo()
                            .search(
                                [
                                    ("script_step_id", "=", step.id),
                                    ("id", "!=", chatbot_message.id),
                                    ("discuss_channel_id", "=", channel.id),
                                ],
                                limit=1,
                            )
                        )
                        step_data["rawAnswer"] = [
                            "markup",
                            user_answer_message.user_raw_answer,
                        ]
                    store.add_model_values("ChatbotStep", step_data)
                    store.add(
                        message,
                        {"chatbotStep": {"scriptStep": step.id, "message": message.id}},
                    )

    def _get_store_partner_name_fields(self):
        if self.channel_id.channel_type == "livechat":
            return self.env["res.partner"]._get_fields_store_livechat_username()
        return super()._get_store_partner_name_fields()
