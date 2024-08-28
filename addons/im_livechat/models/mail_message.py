# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = 'mail.message'

    parent_author_name = fields.Char(compute="_compute_parent_author_name")
    parent_body = fields.Html(compute="_compute_parent_body")

    @api.depends('parent_id')
    def _compute_parent_author_name(self):
        for message in self:
            author = message.parent_id.author_id or message.parent_id.author_guest_id
            message.parent_author_name = author.name if author else False

    @api.depends('parent_id.body')
    def _compute_parent_body(self):
        for message in self:
            message.parent_body = message.parent_id.body if message.parent_id else False

    def _to_store(self, store: Store, **kwargs):
        """If we are currently running a chatbot.script, we include the information about
        the chatbot.message related to this mail.message.
        This allows the frontend display to include the additional features
        (e.g: Show additional buttons with the available answers for this step)."""
        super()._to_store(store, **kwargs)
        channel_messages = self.filtered(lambda message: message.model == "discuss.channel")
        channel_by_message = channel_messages._record_by_message()
        for message in channel_messages.filtered(
            lambda message: channel_by_message[message].channel_type == "livechat"
        ):
            channel = channel_by_message[message]
            # sudo: chatbot.script.step - checking whether the current message is from chatbot
            chatbot = channel.chatbot_current_step_id.sudo().chatbot_script_id.operator_partner_id
            if (channel.chatbot_current_step_id and message.author_id == chatbot):
                chatbot_message = (
                    self.env["chatbot.message"]
                    .sudo()
                    .search([("mail_message_id", "=", message.id)], limit=1)
                )
                if step := chatbot_message.script_step_id:
                    step_data = {
                        "id": (step.id, channel.id),
                        "message": Store.one(message, only_id=True),
                        "scriptStep": Store.one(step, only_id=True),
                        "operatorFound": step.step_type == "forward_operator"
                        and len(channel.channel_member_ids) > 2,
                    }
                    if answer := chatbot_message.user_script_answer_id:
                        step_data["selectedAnswer"] = Store.one(answer, only_id=True)
                    store.add("ChatbotStep", step_data)
                    store.add(
                        message,
                        {"chatbotStep": {"scriptStep": step.id, "message": message.id}},
                    )

    def _author_to_store(self, store: Store):
        messages_w_author_channel = self.filtered(
            lambda message: message.author_id
            and message.model == "discuss.channel"
            and message.res_id
        )
        channel_by_message = messages_w_author_channel._record_by_message()
        messages_w_author_livechat = messages_w_author_channel.filtered(
            lambda message: channel_by_message[message].channel_type == "livechat"
        )
        super(MailMessage, self - messages_w_author_livechat)._author_to_store(store)
        for message in messages_w_author_livechat:
            store.add(
                message,
                {
                    "author": Store.one(
                        message.author_id,
                        fields=["is_company", "user_livechat_username", "user", "write_date"],
                    ),
                },
            )
