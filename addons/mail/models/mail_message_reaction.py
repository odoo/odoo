# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.tools import groupby
from odoo.addons.mail.tools.discuss import Store


class MailMessageReaction(models.Model):
    _name = 'mail.message.reaction'
    _description = 'Message Reaction'
    _order = 'id desc'
    _log_access = False

    message_id = fields.Many2one(string="Message", comodel_name='mail.message', ondelete='cascade', required=True, readonly=True)
    content = fields.Char(string="Content", required=True, readonly=True)
    partner_id = fields.Many2one(string="Reacting Partner", comodel_name='res.partner', ondelete='cascade', readonly=True)
    guest_id = fields.Many2one(string="Reacting Guest", comodel_name='mail.guest', ondelete='cascade', readonly=True)

    def init(self):
        self.env.cr.execute("CREATE UNIQUE INDEX IF NOT EXISTS mail_message_reaction_partner_unique ON %s (message_id, content, partner_id) WHERE partner_id IS NOT NULL" % self._table)
        self.env.cr.execute("CREATE UNIQUE INDEX IF NOT EXISTS mail_message_reaction_guest_unique ON %s (message_id, content, guest_id) WHERE guest_id IS NOT NULL" % self._table)

    _sql_constraints = [
        ("partner_or_guest_exists", "CHECK((partner_id IS NOT NULL AND guest_id IS NULL) OR (partner_id IS NULL AND guest_id IS NOT NULL))", "A message reaction must be from a partner or from a guest."),
    ]

    def _to_store(self, store: Store):
        for (message_id, content), reactions in groupby(self, lambda r: (r.message_id, r.content)):
            reactions = self.env["mail.message.reaction"].union(*reactions)
            store.add(reactions.guest_id, fields=["avatar_128", "name"])
            store.add(reactions.partner_id, fields=["avatar_128", "name"])
            data = {
                "content": content,
                "count": len(reactions),
                "sequence": min(reactions.ids),
                "personas": Store.many_ids(reactions.guest_id)
                + Store.many_ids(reactions.partner_id),
                "message": Store.one_id(message_id),
            }
            store.add("MessageReactions", data)
