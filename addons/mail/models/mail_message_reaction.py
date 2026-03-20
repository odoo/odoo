# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.tools import groupby
from odoo.addons.mail.tools.discuss import Store


class MailMessageReaction(models.Model):
    _name = 'mail.message.reaction'
    _description = 'Message Reaction'
    _order = 'id desc'
    _log_access = False

    message_id = fields.Many2one(string="Message", comodel_name='mail.message', ondelete='cascade', required=True, readonly=True, index=True)
    content = fields.Char(string="Content", required=True, readonly=True)
    partner_id = fields.Many2one(string="Reacting Partner", comodel_name='res.partner', ondelete='cascade', readonly=True)
    guest_id = fields.Many2one(string="Reacting Guest", comodel_name='mail.guest', ondelete='cascade', readonly=True)

    _partner_unique = models.UniqueIndex("(message_id, content, partner_id) WHERE partner_id IS NOT NULL")
    _guest_unique = models.UniqueIndex("(message_id, content, guest_id) WHERE guest_id IS NOT NULL")

    _partner_or_guest_exists = models.Constraint(
        'CHECK((partner_id IS NOT NULL AND guest_id IS NULL) OR (partner_id IS NULL AND guest_id IS NOT NULL))',
        'A message reaction must be from a partner or from a guest.',
    )

    def _to_store(self, store: Store, res: Store.FieldList):
        if res:
            raise NotImplementedError("Fields are not supported for reactions.")
        for (message, content), reactions in groupby(self, lambda r: (r.message_id, r.content)):
            reactions = self.env["mail.message.reaction"].union(*reactions)
            store.add_model_values(
                "MessageReactions",
                lambda res, content=content, message=message, reactions=reactions: (
                    res.attr("content", content),
                    res.attr("count", len(reactions)),
                    res.many("guests", "_store_avatar_fields", value=reactions.guest_id),
                    res.attr("message", message.id),
                    res.many(
                        "partners",
                        lambda res: (
                            res.from_method("_store_avatar_fields"),
                            message._store_partner_name_dynamic_fields(res),
                        ),
                        value=reactions.partner_id,
                    ),
                    res.attr("sequence", min(reactions.ids)),
                ),
            )
