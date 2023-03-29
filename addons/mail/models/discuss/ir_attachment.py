# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _bus_notification_target(self):
        self.ensure_one()
        if self.res_model == "discuss.channel" and self.res_id:
            return self.env["discuss.channel"].browse(self.res_id)
        guest = self.env["mail.guest"]._get_guest_from_context()
        if self.env.user._is_public() and guest:
            return guest
        return super()._bus_notification_target()

    @api.model
    def _get_upload_env(self, request, thread_model, thread_id):
        """Overriden to allow guests and (portal) users to upload attachments to channels they have
        access to. The base method returns the env of the current request, which is not sudo and
        relies on access rights. Guests or (portal) users need sudo to upload attachments."""
        if thread_model == "discuss.channel":
            return (
                request.env["discuss.channel.member"]
                ._get_as_sudo_from_request_or_raise(request=request, channel_id=int(thread_id))
                .env
            )
        return super()._get_upload_env(request, thread_model, thread_id)

    def _prepare_attachment_format(self, attachment):
        attachment_format = super()._prepare_attachment_format(attachment)
        voice = self.env["discuss.voice.metadata"].sudo().search([("attachment_id", "=", attachment.id)])
        if voice:
            attachment_format['duration'] = voice.duration
        return attachment_format

    def create_uploaded_attachment(self, vals, **kwargs):
        attachment = super(IrAttachment, self).create_uploaded_attachment(vals)
        if kwargs.get('duration'):
            attachment.env["discuss.voice.metadata"].create({
                "attachment_id": attachment.id,
                "duration": kwargs['duration'],
            })
        return attachment
