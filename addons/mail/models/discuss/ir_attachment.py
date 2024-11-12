# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons.mail.tools.discuss import Store


class IrAttachment(models.Model):
    _inherit = ["ir.attachment"]

    is_voice = fields.Boolean("Is Voice")
    # voice_ids = fields.One2many("discuss.voice.metadata", "attachment_id")

    # def _compute_is_voice(self):
    #     voice_data = dict(self.env['discuss.voice.metadata'].sudo()._read_group(
    #         [('attachment_id', 'in', self.ids)], groupby=['attachment_id'], aggregates=['id:recordset'],
    #     )) if self else {}
    #     for attachment in self:
    #         attachment.is_voice = attachment in voice_data

    # def _inverse_is_voice(self):
    #     todo = self.sudo().filtered(lambda a: a.is_voice and not a.voice_ids)
    #     if todo:
    #         self.env["discuss.voice.metadata"].create([{"attachment_id": att.id} for att in todo])
    #     self.filtered(lambda a: not a.is_voice).sudo().voice_ids.unlink()

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
            # TODO master: make a real computed / inverse field and stop propagating
            # kwargs through hook methods
            # sudo: discuss.voice.metadata - checking the existence of voice metadata for accessible attachments is fine
            store.add(attachment, {"voice": attachment.is_voice})
