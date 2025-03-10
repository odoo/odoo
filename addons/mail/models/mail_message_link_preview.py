# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.mail.tools.discuss import Store


class MessageMailLinkPreview(models.Model):
    _name = "mail.message.link.preview"
    _inherit = ["bus.listener.mixin"]
    _description = "Link between link previews and messages"
    _order = "sequence, id"

    message_id = fields.Many2one("mail.message", required=True, ondelete="cascade")
    link_preview_id = fields.Many2one(
        "mail.link.preview", index=True, required=True, ondelete="cascade"
    )
    sequence = fields.Integer("Sequence")
    is_hidden = fields.Boolean()
    author_id = fields.Many2one(related="message_id.author_id")

    _unique_message_link_preview = models.UniqueIndex("(message_id, link_preview_id)")
    _message_id_not_null = models.Constraint("CHECK(message_id IS NOT NULL)")
    _link_preview_id_not_null = models.Constraint("CHECK(link_preview_id IS NOT NULL)")

    def _bus_channel(self):
        return self.message_id._bus_channel()

    def _hide_and_notify(self):
        if not self:
            return True
        self.is_hidden = True
        for message_link_preview in self:
            self._bus_send_store(Store().delete(message_link_preview))

    def _unlink_and_notify(self):
        if not self:
            return True
        for message_link_preview in self:
            self._bus_send_store(Store().delete(message_link_preview))
        self.unlink()

    def _to_store_defaults(self):
        return [
            Store.One("link_preview_id", sudo=True),
            Store.One("message_id", [], sudo=True),
        ]
