import typing

from odoo import fields, models
from odoo.libs.debug_log import DebugLog

from odoo.addons.mail.tools.discuss import Store, StoreFieldsInput

if typing.TYPE_CHECKING:
    from .mail_link_preview import MailLinkPreview
    from .mail_message import MailMessage
    from .res_partner import ResPartner

_debug = DebugLog(__name__)


class MessageMailLinkPreview(models.Model):
    _name = "mail.message.link.preview"
    _inherit = ["mixin.bus.listener"]
    _description = "Link between link previews and messages"
    _order = "sequence, id"

    message_id: MailMessage = fields.Many2one(
        comodel_name="mail.message",
        index=True,
        required=True,
        ondelete="cascade",
    )
    link_preview_id: MailLinkPreview = fields.Many2one(
        comodel_name="mail.link.preview",
        index=True,
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer()
    is_hidden = fields.Boolean()
    author_id: ResPartner = fields.Many2one(related="message_id.author_id")

    _unique_message_link_preview = models.UniqueIndex("(message_id, link_preview_id)")

    def _bus_channel(self) -> models.Model:
        return self.message_id._bus_channel()

    def _hide_and_notify(self) -> None:
        if not self:
            return
        _debug.lifecycle("hidden", previews=self.ids)
        self.is_hidden = True
        for message_link_preview in self:
            Store(bus_channel=message_link_preview._bus_channel()).add_deletion(
                message_link_preview
            ).bus_send()

    def _unlink_and_notify(self) -> None:
        if not self:
            return
        _debug.lifecycle("unlinked", previews=self.ids)
        for message_link_preview in self:
            Store(bus_channel=message_link_preview._bus_channel()).add_deletion(
                message_link_preview
            ).bus_send()
        self.unlink()

    def _to_store_defaults(self, target: Store.Target) -> StoreFieldsInput:
        return [
            Store.One("link_preview_id", sudo=True),
            Store.One("message_id", [], sudo=True),
        ]
