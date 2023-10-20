# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class Message(models.Model):
    _inherit = "mail.message"
    _populate_dependencies = ["res.partner", "res.users"]

    def _populate(self, size):
        return super()._populate(size) + self._populate_threads(size, "res.partner")

    def _populate_threads(self, size, model_name):
        comment_subtype = self.env.ref('mail.mt_comment')
        note_subtype = self.env.ref('mail.mt_note')
        random = populate.Random("mail.message")
        partners = self.env["res.partner"].browse(self.env.registry.populated_models["res.partner"])
        threads = self.env[model_name].browse(self.env.registry.populated_models[model_name])
        admin = self.env.ref("base.user_admin").partner_id
        messages = []
        for thread in threads:
            for counter in range(random.randrange({"small": 10, "medium": 100, "large": 1000}[size])):
                author = random.choice(admin + partners)
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
        return self.env["mail.message"].create(messages)
