from odoo import fields, models
from odoo.addons.mail.tools.discuss import Store


class MessageMailLinkPreview(models.Model):
    _name = "mail.message.link.preview"
    _inherit = ["bus.listener.mixin"]
    _description = "Link between link previews and messages"

    link_preview_id = fields.Many2one(
        "mail.link.preview", index=True, required=True, ondelete="cascade"
    )
    message_id = fields.Many2one("mail.message", ondelete="cascade")
    is_hidden = fields.Boolean()
    author_id = fields.Many2one(related="message_id.author_id")
    preview = fields.Char(related="message_id.preview")

    _unique_message_link_preview = models.UniqueIndex("(message_id, link_preview_id)")

    def _bus_channel(self):
        return self.message_id._bus_channel()

    def _hide_and_notify(self):
        if not self:
            return True
        self.is_hidden = True
        for message_link_preview in self:
            self._bus_send_store(Store(message_link_preview).delete(message_link_preview))

    def _unlink_and_notify(self):
        if not self:
            return True
        for message_link_preview in self:
            self._bus_send_store(message_link_preview)
        self.unlink()

    def _to_store_defaults(self):
        return [
            Store.One("link_preview_id", sudo=True),
            Store.One("message_id", [], sudo=True),
        ]
