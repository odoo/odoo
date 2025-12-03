from odoo import models
from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _store_message_fields(self, res: Store.FieldList, **kwargs):
        super()._store_message_fields(res, **kwargs)
        res.attr("chatbot_current_step")

    def _to_store(self, store: Store, res: Store.FieldList):
        """If we are currently running a chatbot.script, we include the information about
        the chatbot.message related to this mail.message.
        This allows the frontend display to include the additional features
        (e.g: Show additional buttons with the available answers for this step)."""
        if add_current_step := "chatbot_current_step" in res:
            res.remove("chatbot_current_step")
        super()._to_store(store, res)
        if not add_current_step:
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

                    def chatbot_step_fields(
                        res: Store.FieldList,
                        chatbot=chatbot,
                        chatbot_message=chatbot_message,
                        channel=channel,
                        message=message,
                        step=step,
                    ):
                        res.attr("id", (step.id, message.id))
                        res.attr("message", message.id)
                        res.one("scriptStep", ["message", "step_type"], value=step)
                        res.attr(
                            "operatorFound",
                            step.is_forward_operator and channel.livechat_operator_id != chatbot,
                        )
                        if answer := chatbot_message.user_script_answer_id:
                            res.attr("selectedAnswer", {"id": answer.id, "label": answer.name})
                        if step.step_type in [
                            "free_input_multi",
                            "free_input_single",
                            "question_email",
                            "question_phone",
                        ]:
                            domain = [
                                ("script_step_id", "=", step.id),
                                ("id", "!=", chatbot_message.id),
                                ("discuss_channel_id", "=", channel.id),
                            ]
                            # sudo: chatbot.message - checking the user answer to the step is allowed
                            user_answer_message = (
                                self.env["chatbot.message"].sudo().search_fetch(domain, limit=1)
                            )
                            res.attr("rawAnswer", user_answer_message.user_raw_answer)

                    store.add_model_values("ChatbotStep", chatbot_step_fields)
                    store.add(
                        message,
                        lambda res, step=step: res.attr(
                            "chatbotStep",
                            value=lambda m: {"scriptStep": step.id, "message": m.id},
                        ),
                    )

    def _store_author_dynamic_fields(self, partner_res: Store.FieldList):
        super()._store_author_dynamic_fields(partner_res)
        if self.channel_id.channel_type == "livechat":
            partner_res.remove("name")
            partner_res.from_method("_store_livechat_username_fields")
