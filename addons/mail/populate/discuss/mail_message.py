# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models
from odoo.tools import populate

_logger = logging.getLogger(__name__)


class Message(models.Model):
    _inherit = "mail.message"

    @property
    def _populate_dependencies(self):
        return super()._populate_dependencies + ["discuss.channel", "discuss.channel.member"]

    def _populate(self, size):
        res = super()._populate(size)
        admin = self.env.ref("base.user_admin").partner_id
        random = populate.Random("mail.message in discuss")
        channels = self.env["discuss.channel"].browse(self.env.registry.populated_models["discuss.channel"])
        messages = []
        big_done = 0
        for channel in channels.filtered(lambda channel: channel.channel_member_ids):
            big = {"small": 80, "medium": 150, "large": 300}[size]
            small_big_ratio = {"small": 10, "medium": 150, "large": 1000}[size]
            max_messages = big if random.randint(1, small_big_ratio) == 1 else 60
            admin_is_member = admin in channel.channel_member_ids.partner_id
            number_messages = 500 if big_done < 2 and admin_is_member else random.randrange(max_messages)
            if number_messages >= 500 and admin_is_member:
                big_done += 1
            for counter in range(number_messages):
                messages.append(
                    {
                        "author_id": random.choice(channel.channel_member_ids.partner_id).id,
                        "body": f"message_body_{counter}",
                        "message_type": "comment",
                        "model": "discuss.channel",
                        "res_id": channel.id,
                    }
                )
        batches = [messages[i : i + 1000] for i in range(0, len(messages), 1000)]
        count = 0
        for batch in batches:
            count += len(batch)
            _logger.info("Batch of mail.message for discuss.channel: %s/%s", count, len(messages))
            res += self.env["mail.message"].create(batch)
        return res
