# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.mail.populate.mail_message import Message as MailMessage
from odoo.tools import populate


class Message(models.Model):
    _inherit = "mail.message"
    _populate_dependencies = ["discuss.channel", "discuss.channel.member"] + MailMessage._populate_dependencies

    def _populate_factories(self):
        channel_ids = self.env.registry.populated_models["discuss.channel"]

        def get_author_id(values, counter, random):
            channel = self.env[values["model"]].browse(values["res_id"])
            channel_member_ids = [channel["id"] for channel in channel.channel_member_ids.read(["id"])]
            return random.choice(channel_member_ids)

        return [
            ("body", populate.constant("message_body_{counter}")),
            ("message_type", populate.constant("comment")),
            ("model", populate.constant("discuss.channel")),
            ("res_id", populate.randomize(channel_ids)),
            ("author_id", populate.compute(get_author_id)),
        ]
