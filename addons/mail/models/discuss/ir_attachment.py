import typing

from odoo import fields, models
from odoo.libs.debug_log import DebugLog

from odoo.addons.mail.tools.discuss import Store, StoreFieldsInput

if typing.TYPE_CHECKING:
    from .discuss_voice_metadata import DiscussVoiceMetadata

_debug = DebugLog(__name__)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    voice_ids: DiscussVoiceMetadata = fields.One2many(
        comodel_name="discuss.voice.metadata",
        inverse_name="attachment_id",
    )

    def _bus_channel(self) -> models.Model:
        self.check_singleton()
        if self.res_model == "discuss.channel" and self.res_id:
            return self.env["discuss.channel"].browse(self.res_id)
        guest = self.env["mail.guest"]._get_guest_from_context()
        if self.env.user._is_public() and guest:
            return guest
        return super()._bus_channel()

    def _to_store_defaults(self, target: Store.Target) -> StoreFieldsInput:
        return super()._to_store_defaults(target) + [
            Store.Many("voice_ids", [], sudo=True)
        ]

    def _post_add_create(self, **kwargs) -> None:
        super()._post_add_create(**kwargs)
        if kwargs.get("voice"):
            self._create_voice_metadata()

    def _create_voice_metadata(self) -> None:
        _debug.lifecycle("voice_metadata_created", attachments=self.ids)
        self.env["discuss.voice.metadata"].create(
            [{"attachment_id": att.id} for att in self]
        )
