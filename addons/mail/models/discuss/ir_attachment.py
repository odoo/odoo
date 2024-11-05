# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons.mail.tools.discuss import Store


class IrAttachment(models.Model):
    _inherit = ["ir.attachment"]

    is_voice = fields.Boolean("Is Voice")

    def _bus_channel(self):
        self.ensure_one()
        if self.res_model == "discuss.channel" and self.res_id:
            return self.env["discuss.channel"].browse(self.res_id)._bus_channel()
        guest = self.env["mail.guest"]._get_guest_from_context()
        if self.env.user._is_public() and guest:
            return guest._bus_channel()
        return super()._bus_channel()

    def _to_store(self, store: Store, **kwargs):
        super()._to_store(store, **kwargs)
        for attachment in self:
            store.add(attachment, {"voice": attachment.is_voice})
