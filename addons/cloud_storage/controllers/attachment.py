# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.http import route, request
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.mail.controllers.attachment import AttachmentController


class CloudAttachmentController(AttachmentController):
    @route()
    @add_guest_to_context
    def mail_attachment_upload(self, ufile, thread_id, thread_model, is_pending=False, **kwargs):
        is_cloud_storage = kwargs.get('cloud_storage')
        if (is_cloud_storage and not request.env['ir.config_parameter'].sudo().get_param('cloud_storage_provider')):
            return request.make_json_response({
                'error': _('Cloud storage configuration has been changed. Please refresh the page.')
            })

        response = super().mail_attachment_upload(ufile, thread_id, thread_model, is_pending, **kwargs)

        if not is_cloud_storage:
            return response

        data = response.json
        if data.get("error"):
            return response

        # append upload url to the response to allow the client to directly
        # upload files to the cloud storage
        attachment = request.env["ir.attachment"].browse(data["data"]["ir.attachment"][0]["id"]).sudo()
        data["upload_info"] = attachment._generate_cloud_storage_upload_info()
        return request.make_json_response(data)
