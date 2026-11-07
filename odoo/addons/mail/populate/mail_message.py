# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models
from odoo.tools import populate

_logger = logging.getLogger(__name__)


class Message(models.Model):
    _inherit = "mail.message"
    _populate_dependencies = ["res.partner", "res.users"]

    def _populate(self, size):
        return super()._populate(size) + self._populate_threads(size, "res.partner")

    def _populate_threads(self, size, model_name):
        comment_subtype = self.env.ref("mail.mt_comment")
        note_subtype = self.env.ref("mail.mt_note")
        random = populate.Random("mail.message")
        partners = self.env["res.partner"].browse(self.env.registry.populated_models["res.partner"])
        threads = self.env[model_name].browse(self.env.registry.populated_models[model_name])
        admin = self.env.ref("base.user_admin").partner_id
        messages = []
        big_done = 0
        for thread in random.sample(threads, k={"small": 30, "medium": 200, "large": 1000}[size]):
            max_messages = {"small": 60, "medium": 200, "large": 1000}[size]
            number_messages = 200 if big_done < 2 else random.randrange(max_messages)
            if number_messages >= 200:
                big_done += 1
            with_admin = False
            for counter in range(number_messages):
                author = admin if not with_admin and random.randint(1, 5) == 1 else random.choice(admin + partners)
                if author == admin:
                    with_admin = True
                message_type = random.choice(["email", "comment"]) if author.partner_share else "comment"
                subtype = comment_subtype if author.partner_share else random.choice(comment_subtype + note_subtype)
                messages.append(
                    {
                        "author_id": author.id,
                        "body": f"message_body_{counter}",
                        "message_type": message_type,
                        "model": "res.partner",
                        "res_id": thread.id,
                        "subtype_id": subtype.id,
                    }
                )
        res = self.env["mail.message"]
        batches = [messages[i : i + 1000] for i in range(0, len(messages), 1000)]
        count = 0
        for batch in batches:
            count += len(batch)
            _logger.info("Batch of mail.message for %s: %s/%s", model_name, count, len(messages))
            res += self.env["mail.message"].create(batch)
        return res
