# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from collections import defaultdict
from odoo.tools import groupby


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

    def _reaction_groups(self):
        reaction_groups = defaultdict(list)
        for (message_id, content), reactions_list in groupby(self, lambda r: (r.message_id.id, r.content)):
            reactions = self.env["mail.message.reaction"].union(*reactions_list)
            reaction_groups[message_id].append({
                "content": content,
                "count": len(reactions),
                "personas": [{"id": guest.id, "name": guest.name, "type": "guest"} for guest in reactions.guest_id] + [
                    {"id": partner.id, "name": partner.name, "type": "partner"} for partner in reactions.partner_id],
                "message": {"id": message_id},
            })
        return reaction_groups
