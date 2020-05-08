# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class PartnerBot(models.Model):
    _name = "res.partner"
    _inherit = "res.partner"

    is_bot = fields.Boolean(default=False)


class ChatBot(models.Model):
    _name = "im_chatbot.chatbot"
    _description = "Chabots"

    name = fields.Char(String="Bot name")
    subject = fields.Char(String="Subject")
    message_ids = fields.One2many("im_chatbot.script", "chatbot_id", index=True)

    livechat_channel_id = 1

    # Each chat bot must have a one res.partner counterpart to have an identity
    # To chat with
    partner_id = fields.Many2one(
        "res.partner", required=True, index=True, ondelete="cascade"
    )

    # When a chatbot is created, create the res.partner to use in the chat box
    @api.model
    def create(self, values):
        res_partner = self.env["res.partner"].create(
            {"name": values["name"], "is_bot": True}
        )
        values["partner_id"] = res_partner["id"]
        result = super(ChatBot, self).create(values)
        return result

    @api.depends("message_ids")
    def test_bot(self):
        for chatbot in self:
            # This seams to get the "connected" user
            partner = self.env.user.partner_id

            # Look like this return a collection of res.partner. Since Odoo doesn't
            # support One2one relation, lets say it will always be the first in
            # this collection
            bot_partner = chatbot.partner_id.read()

            # Create a discution channel between a bot and the current user.
            channel = (
                self.env["mail.channel"]
                # this "with_context" was present on odoobot code. Copy/past and hope it's ok
                .with_context(mail_create_nosubscribe=True).create(
                    {
                        "name": "test",
                        "channel_partner_ids": [(4, bot_partner[0]["id"]), (4, partner.id)],
                        "livechat_channel_id": 1,
                        "livechat_operator_id": bot_partner[0]["id"],
                        "channel_type": "livechat",
                        "public": "private",
                        "email_send": False,
                        "country_id": 1,
                        "livechat_active": True,
                    }
                )
            )

            self.env["bus.bus"].sendone(
                (self._cr.dbname, "res.partner", partner.id),
                channel.channel_info("channel_minimize"),
            )

            # Get the messages sequence.
            messages = chatbot.message_ids.read()

            # Extract the first message. Since messages are ordered by
            # sequence, the [0] containt the first message.
            first_message = messages[0]["name"]

            # Post a message to the channel
            channel.sudo().message_post(
                body=first_message,
                author_id=bot_partner[0]["id"],
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
            return channel


# class ImLivechatChannel(models.Model):
#     _name = "im_livechat.channel"
#     _inherit = "im_livechat.channel"

#     nb_chatbot = fields.Integer(compute="_compute_nb_chatbot")

#     @api.depends("chatbot_ids")
#     def _compute_nb_chatbot(self):
#         for channel in self:
#             channel.nb_chatbot = len(channel.chatbot_ids)
