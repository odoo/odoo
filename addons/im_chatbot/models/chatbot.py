# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class PartnerBot(models.Model):
    _inherit = "res.partner"
    _description = "Add chatbot information on the res.partner model"

    is_bot = fields.Boolean(default=False)
    chatbot_ids = fields.One2many("im_chatbot.chatbot", "partner_id")


class ChatbotMailMessage(models.Model):
    _inherit = "mail.message"
    _description = "Add script information for the chatbots"

    script_id = fields.Many2one("im_chatbot.script")


class ChatBot(models.Model):
    _name = "im_chatbot.chatbot"
    _description = "Chabots main table"

    name = fields.Char(String="Bot name")
    subject = fields.Char(String="Subject")
    message_ids = fields.One2many("im_chatbot.script", "chatbot_id", index=True)

    livechat_channel_id = fields.One2many("im_livechat.channel", "chatbot_id")

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
            bot_partner = chatbot.partner_id

            # Create a discution channel between a bot and the current user.
            channel = (
                self.env["mail.channel"]
                .with_context(mail_create_nosubscribe=True).create(
                    {
                        "name": "test",
                        "channel_partner_ids": [
                            (4, bot_partner[0]["id"]),
                            (4, partner.id),
                        ],
                        "livechat_channel_id": chatbot.livechat_channel_id[0]["id"],
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
            messages = chatbot.message_ids

            # Extract the first message. Since messages are ordered by
            # sequence, the [0] containt the first message.
            first_message = messages[0]

            # Post a message to the channel
            channel._bot_message_post(bot_partner[0], first_message)
            return channel


class ChatbotMessageHook(models.Model):
    _inherit = "mail.channel"

    # This is where the bot "catch" the conversation. And the user response
    def _message_post_after_hook(self, message, msg_vals):
        super(ChatbotMessageHook, self)._message_post_after_hook(message, msg_vals)

        # Livechat Channel opérator is a bot but not the one who posted
        # We know the bot can read the message and react to it
        if (
            self.channel_type == "livechat"
            and self.livechat_operator_id.is_bot
            and not message.author_id.is_bot
        ):
            self._bot_answer(message)

    def _bot_answer(self, user_message):
        # Get the "bot operator"
        bot_partner = self.livechat_operator_id

        # We need to know witch script is next
        chatbot = bot_partner.chatbot_ids[0]

        # Exctract the message from the chatbot
        # They are linked to a script_id
        chatbot_messages = (
            self.channel_message_ids
            # Only the chatbot message
            .filtered(lambda message: message.script_id)
            # First message is the last message send by the bot
            .sorted(lambda message: message.id, reverse=True)
        )

        # This get the sequence of the last message send by the bot.
        current_sequence = chatbot_messages[0].script_id.read(["sequence"])[0][
            "sequence"
        ]

        # Get the next message in the squence
        next_message = self.env["im_chatbot.script"].search(
            [("chatbot_id", "=", chatbot.id), ("sequence", ">", current_sequence)]
        )

        # Sent the next message
        self._bot_message_post(bot_partner, next_message[0])
        return True

    def _bot_message_post(self, bot_partner, message):
        self.sudo().message_post(
            body=message.name,
            author_id=bot_partner.id,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        ).write({"script_id": message.id})

        return True


class ImLivechatChannel(models.Model):
    _inherit = "im_livechat.channel"

    chatbot_id = fields.Many2one('im_chatbot.chatbot')

    # nb_chatbot = fields.Integer(compute="_compute_nb_chatbot")

    # @api.depends("chatbot_ids")
    # def _compute_nb_chatbot(self):
    #     for channel in self:
    #         channel.nb_chatbot = len(channel.chatbot_ids)
