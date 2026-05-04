from odoo import models, fields
from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = 'mail.message'

    chatbot_message_ids = fields.One2many("chatbot.message", "mail_message_id")

    def _store_message_fields(self, res: Store.FieldList, **kwargs):
        super()._store_message_fields(res, **kwargs)

        def is_chatbot_authored(message):
            return (
                message.channel_id.channel_type == "livechat" and
                message.channel_id.chatbot_current_step_id and
                message.channel_id.chatbot_current_step_id.sudo().chatbot_script_id.operator_partner_id
                == message.author_id
            )

        def chatbot_step_data(message):
            chatbot_message = message.sudo().chatbot_message_ids[:1]
            if not chatbot_message.script_step_id:
                return False
            answer = chatbot_message.user_script_answer_id
            return {
                "scriptStep": chatbot_message.script_step_id.id,
                "message": message.id,
                "operatorFound":
                    chatbot_message.script_step_id.step_type == "forward_operator" and
                    # sudo: discuss.channel - visitors/guests can check if an operator exists
                    bool(message.channel_id.sudo().livechat_agent_partner_ids),
                "selectedAnswer": answer.id if answer else False,
                "user_answer_chatbot_message_ids": chatbot_message.user_answer_chatbot_message_ids.ids,
            }

        res.attr("chatbotStep", value=chatbot_step_data, predicate=is_chatbot_authored)
        res.many(
            "chatbot_message_ids",
            lambda res: (
                res.one("script_step_id", ["message", "step_type"]),
                res.one("user_script_answer_id", ["name"]),
                res.many("user_answer_chatbot_message_ids",
                    lambda res: res.one("mail_message_id", ["body"]),
                ),
            ),
            only_data=True,
            predicate=is_chatbot_authored,
            sudo=True,
        )

    def _store_partner_name_dynamic_fields(self, partner_res: Store.FieldList):
        super()._store_partner_name_dynamic_fields(partner_res)
        if self.channel_id.channel_type == "livechat":
            partner_res.remove("name")
            partner_res.from_method("_store_livechat_username_fields")
