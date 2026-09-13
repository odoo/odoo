import typing

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

from odoo.addons.mail.tools.discuss import Store, StoreFieldsInput

if typing.TYPE_CHECKING:
    from .discuss_call_history import DiscussCallHistory
    from .discuss_channel import DiscussChannel

_debug = DebugLog(__name__)


class MailMessage(models.Model):
    _inherit = "mail.message"

    call_history_ids: DiscussCallHistory = fields.One2many(
        comodel_name="discuss.call.history",
        inverse_name="start_call_message_id",
    )
    channel_id: DiscussChannel = fields.Many2one(
        comodel_name="discuss.channel",
        compute="_compute_channel_id",
    )

    @api.depends("model", "res_id")
    def _compute_channel_id(self) -> None:
        for message in self:
            if message.model == "discuss.channel" and message.res_id:
                message.channel_id = self.env["discuss.channel"].browse(message.res_id)
            else:
                message.channel_id = False

    def _to_store_defaults(self, target: Store.Target) -> StoreFieldsInput:
        return super()._to_store_defaults(target) + [
            Store.Many(
                "call_history_ids",
                ["duration_hour", "end_dt"],
                predicate=lambda m: m.body and 'data-oe-type="call"' in m.body,
            ),
        ]

    def _extras_to_store(self, store: Store, format_reply: bool) -> None:
        super()._extras_to_store(store, format_reply=format_reply)
        if format_reply:
            store.add(
                self.sudo().filtered(lambda message: message.channel_id),
                Store.One(
                    "parent_id",
                    format_reply=False,
                    predicate=lambda message: (
                        not message.parent_id
                        or (
                            message.parent_id.model == message.model
                            and message.parent_id.res_id == message.res_id
                        )
                    ),
                ),
            )

    def _bus_channel(self) -> models.Model:
        self.check_singleton()
        if self.channel_id:
            return self.channel_id
        guest = self.env["mail.guest"]._get_guest_from_context()
        if self.env.user._is_public() and guest:
            _debug.logic("bus_channel", message=self.id, by="guest", guest=guest.id)
            return guest
        return super()._bus_channel()
