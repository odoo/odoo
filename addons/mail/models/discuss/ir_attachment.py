# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    voice_ids = fields.One2many("discuss.voice.metadata", "attachment_id")

    def _bus_notification_target(self):
        self.ensure_one()
        if self.res_model == "discuss.channel" and self.res_id:
            return self.env["discuss.channel"].browse(self.res_id)
        guest = self.env["mail.guest"]._get_guest_from_context()
        if self.env.user._is_public() and guest:
            return guest
        return super()._bus_notification_target()

    @api.model
    def _get_upload_env(self, thread_model, thread_id):
        """Overriden to allow guests and (portal) users to upload attachments to channels they have
        access to. The base method returns the env of the current request, which is not sudo and
        relies on access rights. Guests or (portal) users need sudo to upload attachments."""
        if thread_model == "discuss.channel":
            return (
                self.env["discuss.channel.member"]
                ._get_as_sudo_from_context_or_raise(channel_id=int(thread_id))
                .env
            )
        return super()._get_upload_env(thread_model, thread_id)

    def _attachment_format(self):
        attachment_format = super()._attachment_format()
        for a in attachment_format:
            a["voice"] = bool(self.browse(a["id"]).with_prefetch(self._prefetch_ids).sudo().voice_ids)
        return attachment_format

    def _post_add_create(self, **kwargs):
        super()._post_add_create()
        if kwargs.get('voice'):
            self.env["discuss.voice.metadata"].create([{"attachment_id": attachment.id} for attachment in self])
