# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons.mail.tools.discuss import Store


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    voice_ids = fields.One2many("discuss.voice.metadata", "attachment_id")

    def _bus_channel(self):
        self.ensure_one()
        if self.res_model == "discuss.channel" and self.res_id:
            return self.env["discuss.channel"].browse(self.res_id)
        guest = self.env["mail.guest"]._get_guest_from_context()
        if self.env.user._is_public() and guest:
            return guest
        return super()._bus_channel()

    def _to_store_defaults(self, target):
        # sudo: discuss.voice.metadata - checking the existence of voice metadata for accessible
        # attachments is fine
        return super()._to_store_defaults(target) + [Store.Many("voice_ids", [], sudo=True)]

    def _post_add_create(self, **kwargs):
        super()._post_add_create(**kwargs)
        if kwargs.get('voice'):
            self._set_voice_metadata()

    def _set_voice_metadata(self):
        self.env["discuss.voice.metadata"].create([{"attachment_id": att.id} for att in self])
