# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class Message(models.Model):
    _inherit = "mail.message"
    _populate_dependencies = ["res.partner"]
    _populate_sizes = {"small": 1000, "medium": 10000, "large": 500000}

    def _populate_factories(self):
        thread_ids = self.env.registry.populated_models["res.partner"]
        return [
            ("body", populate.constant("message_body_{counter}")),
            ("message_type", populate.constant("comment")),
            ("model", populate.constant("res.partner")),
            ("res_id", populate.randomize(thread_ids)),
            ("author_id", populate.randomize(thread_ids)),
        ]

    def _populate(self, size):
        res = super()._populate(size)
        partner = self.env.ref("base.user_admin").partner_id
        # create 100 in the chatter of the res.partner admin
        messages = []
        for counter in range(100):
            messages.append(
                {
                    "body": f"message_body_{counter}",
                    "message_type": "comment",
                    "model": "res.partner",
                    "res_id": partner.id,
                    "author_id": partner.id,
                }
            )
        return res + self.env["mail.message"].create(messages)
