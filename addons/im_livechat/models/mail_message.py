from odoo import models
from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _to_store_defaults(self, target):
        return super()._to_store_defaults(target) + ["chatbot_current_step"]

    def _to_store(self, store: Store, fields, **kwargs):
        """If we are currently running a chatbot.script, we include the information about
        the chatbot.message related to this mail.message.
        This allows the frontend display to include the additional features
        (e.g: Show additional buttons with the available answers for this step)."""
        super()._to_store(store, [f for f in fields if f != "chatbot_current_step"], **kwargs)
        if "chatbot_current_step" not in fields:
            return
        channel_messages = self.filtered(lambda message: message.channel_id)
        channel_by_message = channel_messages._record_by_message()
        for message in channel_messages.filtered(
            lambda message: channel_by_message[message].channel_type == "livechat"
        ):
            channel = channel_by_message[message]
            # sudo: chatbot.script.step - checking whether the current message is from chatbot
            chatbot = channel.chatbot_current_step_id.sudo().chatbot_script_id.operator_partner_id
            if channel.chatbot_current_step_id and message.author_id == chatbot:
                chatbot_message = (
                    self.env["chatbot.message"]
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
                        # sudo: chatbot.message - checking the user answer to the step is allowed
                        user_answer_message = (
                            self.env["chatbot.message"]
                            .sudo()
                            .search(
                                [
                                    ("script_step_id", "=", step.id),
                                    ("id", "!=", chatbot_message.id),
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
                        message, {"chatbotStep": {"scriptStep": step.id, "message": message.id}}
                    )

    def _get_store_partner_name_fields(self):
        if self.channel_id.channel_type == "livechat":
            return self.env["res.partner"]._get_store_livechat_username_fields()
        return super()._get_store_partner_name_fields()
