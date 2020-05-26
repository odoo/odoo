# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.http import request


class PartnerBot(models.Model):
    _inherit = "res.partner"
    _description = "Add chatbot information on the res.partner model"

    is_bot = fields.Boolean(default=False)
    chatbot_ids = fields.One2many("im_chatbot.chatbot", "partner_id")


class ChatBot(models.Model):
    _name = "im_chatbot.chatbot"
    _description = "Chabots main table"

    name = fields.Char(Required=True, String="Subject")
    livechat_username = fields.Char(Required=True, String="Bot name")
    message_ids = fields.One2many("im_chatbot.script", "chatbot_id", index=True)

    livechat_channel_id = fields.One2many("im_livechat.channel", "chatbot_id")

    # Each chat bot must have a one res.partner counterpart to have an identity
    # To chat with
    partner_id = fields.Many2one(
        "res.partner", required=True, index=True, ondelete="cascade"
    )

    def _init_chatbot(self, script = []):
        """
        This set the chatbot script and the script pointer inside the session
        """
        request.session["im_chatbot_script"] = script
        request.session["im_chatbot_script_pointer"] = 0

    def _action_engine(self, channel, action=''):
        if action == "lead":
            self._action_lead_script()
        channel._bot_answer()

    def _action_lead_script(self):
        script = [
            {
                "name": _("Name of this lead"),
                "answer_type": "input",
                "field": "name" # Field key is the field of the model
            },
            {
                "name": _("Notes ?"),
                "answer_type": "input",
                "field": "description"
            },
            {
                "name": _("Thanks ! See you soon !"),
                "action": "_create_lead"
            }
        ]
        self._init_chatbot(script)
        return True

    def _create_lead(self, channel):

        lead = self.env["crm.lead"].create({
            "name": "test",
            "description": "Description test",
            "type": "lead"
        })

    @api.model
    def create(self, values):
        # When a chatbot is created, create the res.partner to use in the chat box
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
                .with_context(mail_create_nosubscribe=True)
                .create(
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

            return channel


class ChatbotChannelHook(models.Model):
    _inherit = "mail.channel"

    @api.model
    def _message_post_after_hook(self, message, msg_vals):
        """
        This is used to catch user answers and store them inside the session
        """
        if "model" in request.session and self.livechat_operator_id.id != message.author_id.id:
            current_script_pointer = request.session["im_chatbot_script_pointer"]-1
            script = request.session["im_chatbot_script"][current_script_pointer]
            if script["answer_type"] == "input" and "field" in script:
                field = request.session["im_chatbot_script"][current_script_pointer]["field"]
                request.session["model"][field] = msg_vals["body"]
                session = request.session["model"]

        return super(ChatbotChannelHook, self)._message_post_after_hook(message, msg_vals)

    def _bot_answer(self):
        """
        This method get the next message on the bot script and send it to
        _bot_message_post to be processed
        """
        # Get the "bot operator"
        bot_partner = self.livechat_operator_id

        # Get the next message from the session
        current_script_pointer = request.session["im_chatbot_script_pointer"]
        next_message = request.session["im_chatbot_script"][current_script_pointer]

        # If the bot answer is an action to perform
        if "action" in next_message:
            action = getattr(bot_partner.chatbot_ids[0], next_message["action"])
            action(self)
        else:
            # Sent the next message
            self._bot_message_post(bot_partner, next_message)

            # Update the pointer to go the next message
            request.session["im_chatbot_script_pointer"] += 1

        return True

    def _bot_message_post(self, bot_partner, script):
        if script["answer_type"] == "input":
            self.sudo().message_post(
                body=script["name"],
                author_id=bot_partner.id,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
        elif script["answer_type"] == "selection":
            qweb = self.env["ir.qweb"]
            self.sudo().message_post(
                body=qweb.render("im_chatbot.multichoice", {"script": script}),
                author_id=bot_partner.id,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )

        return True


class ImLivechatChannel(models.Model):
    _inherit = "im_livechat.channel"

    chatbot_id = fields.Many2one("im_chatbot.chatbot")

    # Add the chatbot to the user available
    def _get_available_users(self):
        available = super(ImLivechatChannel, self)._get_available_users()
        # if not len(available):
        self.chatbot_id._init_chatbot(self.chatbot_id.message_ids.read())
        available = self.chatbot_id

        return available
